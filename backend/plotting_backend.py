import re
import sys
from typing import List

import dash_cytoscape as cyto
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import pyariadne as ari

from systems import tutorial_system


def plot_trajectory(polytopes_df, var_x, var_y, var_z=None, use_mesh=False):
    """
    Plot the provided dataframe over the provided axes a set of polylines. If the dataframe is a punctual representation (collapse=True) then a scatter plot
    is performed instead, while if `use_mesh` is True then Mesh3D objects will be used instead.
    
    :param polytopes_df: a dataframe obtained via the `orbit_to_dataframe()` method
    :param var_x: the x axis
    :param var_y: the y axis
    :param var_z: optional, the z axis
    :param use_mesh: for 3D plots, use Mesh3D instead of 3D polyline (this is very slow)
    :return: a Plotly figure
    """
    
    is_punctual = polytopes_df['_polytope_id'].value_counts(sort=False).min() < 2
    if var_z is None:
        if is_punctual:
            fig = px.scatter(polytopes_df, x=var_x, y=var_y,
                             color="_loc")
        else:
            fig = px.line(polytopes_df, x=var_x, y=var_y,
                          color="_loc", line_group="_polytope_id")
    else:
        if is_punctual:
            fig = px.scatter_3d(polytopes_df, x=var_x, y=var_y, z=var_z,
                                color="_loc")
        else:
            if not use_mesh:
                fig = px.line_3d(polytopes_df, x=var_x, y=var_y, z=var_z,
                                 color="_loc", line_group="_polytope_id")
            else:
                # 3D meshes are better when dealing with PDEs, but usually here we deal with ODEs
                locations = polytopes_df['_loc'].unique().tolist()
                colors = {loc: i for loc, i in zip(locations, range(len(locations)))}
                fig = go.Figure(
                    data=[
                        go.Mesh3d(x=polytope[var_x], y=polytope[var_y], z=polytope[var_z],
                                  alphahull=0, opacity=0.75, color=colors[polytope['_loc'].unique()[0]])  # FIXME color not properly working
                        for _, polytope in polytopes_df.groupby('_polytope_id')
                    ],
                    # FIXME labels not working
                    layout={
                        'scene': {
                            'xaxis': {'title': {'text': var_x}},
                            'yaxis': {'title': {'text': var_y}},
                            'zaxis': {'title': {'text': var_z}}
                        }
                    }
                )
    
    fig.update_layout(
        legend_title_text='Location',
        transition_duration=500
    )
    return fig


def get_all_variables(system):
    """
    Obtain all the variables (dynamic and auxiliary) of the system.
    
    :param system: the Ariadne `HybridAutomaton`
    :return: a list of variable names, as strings
    """
    
    def filter_variables(equation):
        # remove 'FUN(' from the equation (which otherwise can be interpreted as variables), then extract the variables
        return [e for e in set(re.findall(r'[\w_]+', re.sub(r'\w+\(', '', str(equation)))) if not e.isnumeric()]
    
    variables = set('t')  # time
    for automaton in system:
        for location in automaton.locations():
            for assignment in automaton.dynamic_assignments(location):
                variables.update(filter_variables(assignment))
            for assignment in automaton.auxiliary_assignments(location):
                variables.update(filter_variables(assignment))
    return list(variables)


@DeprecationWarning
def _get_vars(orbit_reach):
    return [orbit_reach[0].state_auxiliary_space().variable(i) for i in range(orbit_reach[0].state_auxiliary_space().dimension())]


# encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(var_x, var_y)
# HybridEnclosure -> LabelledEnclosure -> ValidatedConstrainedImageSet -> ValidatedAffineConstrainedImageSet -> List<Point2d>
#    |                      |                             |                                |                          |
#    \_ location-set tuple  |                             |                                |                          \_ vertices of the polytope
#                           |                             |                                |
#                           \_ set of symbolic variables  |                                |
#                                                         |                                |
#                                                         \_ set on a N-D Euclidean space  |
#                                                                                          |
#                                                                                          \_ 2D projection of the set on 2 variables (es. time/aperture)
#                                                                                             the variables appear in the following order
#                                                                                             1) differentiable variables (in alphabetical order),
#                                                                                             2) time,
#                                                                                             3) auxiliary variables (in alphabetical order)
def orbit_to_dataframe(orbit_reach: ari.HybridEnclosureListSet, var_list: List[str], collapse=False):
    """
    Transforms an Ariadne orbit reach to a Pandas dataframe, allowing immediate Plotly Express plotting.
    
    Each dataframe contains the '_polytope_id', '_loc' and '_time' columns, and a column for every variable in `var_list`. The list of variables is provided
    to extract only the required values. When `var_list = []` or `var_list = ['t']` no extra columns is added and and empty dataframe, still with all the
    columns, is returned.
    
    The `collapse` parameter is quite tricky: everytime `len(var_list) == 2` the data is obtained using Ariadne's `projection(Variables2d(*))` methods,
    which extracts the polytopes projected in the particular projection plane (i.e. the `Variables2d(*)` plane). Those projections are "rigorous" in the
    sense that no extra manipulation is performed on the data. When `len(var_list) >= 3`, since Ariadne doesn't provide a way of projecting onto N-D spaces,
    a series of 2D projections is performed instead: this allows us to have a set of rigorous time/variable projections, but no extra information is
    obtainable about the relationship between the vertices of the various polytopes, which can indeed vary in the number of vertices; to break ties,
    for each set of polytope projection we keep the minimum number of vertices found, but another problem persists. Since we have no way of rigorously
    reconstruct N-D polytopes by their 2D projections, two options are available:
     - ignore the truncation and just save the polytopes "as they are", which means we will have less appealing plots
     - collapse the polytopes to their barycenter, producing a less representative but more appealing plot
    
    :param orbit_reach: the Ariadne `orbit.reach()` result
    :param var_list: the list of variables we want to extract
    :param collapse: collapse higher dimensional polytopes to their barycenter (a single point)
    :return: a dataframe representing the flattened version of the provided `orbit_reach`
    """
    
    def extract_points(points_2d):
        x, y = [p.x for p in points_2d], [p.y for p in points_2d]
        if collapse:
            return sum(x) / len(points_2d), sum(y) / len(points_2d)
        else:
            return x + [x[0]], y + [y[0]]
    
    # manually extract time variable because each axes is constructed against it
    var_list = var_list.copy()
    require_time = 't' in var_list
    if require_time:
        var_list.remove('t')
    
    # return empty
    if len(var_list) == 0:
        df = pd.DataFrame()
        df['_polytope_id'] = df.index + 1
        df['_loc'] = pd.Series()
        df['_time'] = pd.Series()
        if require_time:
            df['t'] = pd.Series()
        return df
    
    polytopes = []
    # projections are 2D, so we need a list of them which will later be joint together
    is_variable_variable = len(var_list) == 2 and not require_time
    if is_variable_variable:
        # just extract the specific axis
        axes = [ari.Variables2d(ari.RealVariable(var_list[0]), ari.RealVariable(var_list[1]))]
    else:
        # extract the time-variable axes and perform a collage
        axes = [ari.Variables2d(ari.TimeVariable(), ari.RealVariable(var_list[i]))
                for i in range(len(var_list))]
    
    # extract the vertices of the polytopes
    for instant, encl in enumerate(orbit_reach):
        # since state/auxiliary variables can change during the evolution, we project them in the required order based on the axes we want
        prj = [ari.projection(encl.state_time_auxiliary_space(), a) for a in axes]
        # we extract the polytope points accordingly to the axes we want
        polytope_points_2d = [encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(p.i, p.j) for p in prj]
        # since the polytope's projections may be different on each axis, we just consider the minimum vertices we got
        # this truncation is idempotent in time-variable and variable-variable cases, but could
        min_prj = min([len(axes_points_2d) for axes_points_2d in polytope_points_2d], default=0)
        
        # avoid punctual polytopes
        if min_prj >= 2:
            # get actual coordinates of the vertices of the polytope
            polytope = {
                '_loc': str(encl.location()),
                '_time': float(str(encl.time_range().upper_bound())),
            }
            if is_variable_variable:
                points = extract_points(polytope_points_2d[0][:min_prj])
                polytope[var_list[0]] = points[0]  # first variable
                polytope[var_list[1]] = points[1]  # second variable
            else:
                if require_time:
                    # add time value (same for each axis, so the first one is enough)
                    polytope['t'] = extract_points(polytope_points_2d[0][:min_prj])[0]  # time is always x, thus [0]
                # add each variable
                polytope.update({
                    var_list[var_i]: extract_points(axes_points_2d[:min_prj])[1]  # variables are always y, thus [1]
                    for var_i, axes_points_2d in enumerate(polytope_points_2d)
                })
            polytopes.append(polytope)
        else:
            print(f'WARNING: instant {instant} polytope has less than 2 vertices', file=sys.stderr)
    
    df = pd.DataFrame(polytopes)
    df['_polytope_id'] = df.index + 1
    var_list = list(set(var_list + (['t'] if require_time else [])))  # remove duplicates
    df = df.explode(var_list)
    return df


def analyze_automaton(automaton: ari.HybridAutomaton, name=None):
    """
    Transform an Ariadne `HybridAutomaton` to a dictionary including all the important information for visualization.
    
    :param automaton: the Ariadne `HybridAutomaton`
    :param name: optional, the name of the automaton, in case `automaton.name() == 'automaton'`
    :return: a dictionary representing the automaton
    """
    
    def explode_location(location):
        # if empty location, the system has one location only, thus the 'model_name' and the '--' location
        return tuple((str(location)[1:-1]).split('|')) if '|' in str(location) else (model_name, '--')
    
    def binding_safe_get(pybind_fun_call):
        try:
            return pybind_fun_call()
        except RuntimeError:
            return None
    
    model_name = str(automaton.name()) if str(automaton.name()) != 'automaton' or name is None else name
    
    info = {
        'name': model_name,
        'locations': {}
    }
    
    for loc in automaton.locations():
        # get location info
        location_name = explode_location(loc)[1]
        info['locations'][location_name] = {
            'name': f'{location_name}',
            'dynamic_assignments': binding_safe_get(lambda: automaton.dynamic_assignments(loc)),
            'dynamic_function': binding_safe_get(lambda: automaton.dynamic_function(loc)),
            'algebraic_assignments': binding_safe_get(lambda: automaton.auxiliary_assignments(loc)),
            'targets': {
                str(event): {
                    'target': explode_location(automaton.target(loc, event))[1],
                    # when this event is output in this location, then we know its kind
                    'event_kind': binding_safe_get(lambda: automaton.event_kind(loc, event).name),
                    # when this event is not an invariant (es. PERMISSIVE), then it has a triggering guard
                    'guard_function': binding_safe_get(lambda: automaton.guard_function(loc, event)),
                    'guard_predicate': binding_safe_get(lambda: automaton.guard_predicate(loc, event)),
                    'invariant_predicate': binding_safe_get(lambda: automaton.invariant_predicate(loc, event)),
                    'reset_assignments': binding_safe_get(lambda: automaton.reset_assignments(loc, event)),
                    'reset_function': binding_safe_get(lambda: automaton.reset_function(loc, event))
                }
                # possible events when in this location
                for event in automaton.events(loc)
            }
        }
    
    return info


def build_cytoscape_graph(automaton_analysis):
    """
    Obtain Cytoscape graph elements (list of nodes and elements)
    
    :param automaton_analysis: the analysis of an automaton obtained by the `analyze_automaton(*)` method
    :return: list of nodes + elements in the Cytoscape format
    """
    
    graph = {
        'nodes': {
            f'node{i}': {
                'data': {
                    'id': location_info['name'],
                    'label': location_info['name']
                }
            }
            for i, location_info in enumerate(automaton_analysis['locations'].values())
        },
        'edges': {
            f'edge{i}': {
                'data': {
                    'source': info[0],
                    'target': info[2],
                    'label': info[1]
                }
            }
            for i, info in enumerate([
                (location_name, event_name, event_info['target'])
                for location_name, location_info in automaton_analysis['locations'].items()
                for event_name, event_info in location_info['targets'].items()
            ])
        }
    }
    nodes = [data for _, data in graph['nodes'].items()]
    edges = [data for _, data in graph['edges'].items()]
    return nodes + edges


def plot_automaton(elements):
    return \
        cyto.Cytoscape(
            id='automaton-cytoscape',
            layout={
                'name': 'circle'
            },
            elements=elements,
            stylesheet=[
                {
                    'selector': 'node',
                    'style': {
                        'label': 'data(label)',
                        'width': '100%',
                        'height': '100%',
                        'text-transform': 'uppercase',
                        'text-valign': 'center',
                        'text-halign': 'center'
                    }
                },
                {
                    'selector': 'edge',
                    'style': {
                        'label': 'data(label)',
                        'curve-style': 'bezier',
                        'control-point-step-size': 75,
                        'loop-direction': 90,
                        'loop-sweep': -45,
                        'target-arrow-shape': 'triangle',
                        'text-rotation': 'autorotate',
                        # TODO improve this to be perpendicular to the edge, not just a vertical shift
                        #  https://github.com/cytoscape/cytoscape.js/issues/965
                        'text-margin-y': -10
                    }
                }
            ],
            responsive=True
        )
