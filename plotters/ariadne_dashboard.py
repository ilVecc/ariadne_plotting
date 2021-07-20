#!/usr/bin/python3
import os.path
import pickle
import sys
from enum import Enum, auto

import dash
import dash_core_components as core
import dash_cytoscape as cyto
import dash_html_components as html
import pandas as pd
import plotly.express as px
import pyariadne as ari
from dash.dependencies import Output, Input, State, MATCH, ALL

import example_system


# encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(var_x, var_y)
# HybridEnclosure -> LabelledEnclosure -> ValidatedConstrainedImageSet -> ValidatedAffineConstrainedImageSet -> List<Point2d>

# HybridEnclosure: coppia locazione-insieme
# LabelledEnclosure: insieme con variabili simboliche
# ValidatedConstrainedImageSet: insieme su spazio euclideo n-dimensionale
# ValidatedAffineConstrainedImageSet: proiezione 2-dimensionale dell'insieme su due variabili (es. tempo/apertura) le variabili sono  in ordine
#                                     1) variabili differenziali in ordine alfabetico,
#                                     2) tempo,
#                                     3) variabili algebriche in ordine alfabetico
# List<Point2d>: date le coordinate del politopo, lista dei vertici del politopo

# Enclosure.location
#          .previous_events
#          .continuous_set
#          .time_range
#          .auxiliary_space
#          .state_space
#          .state_auxiliary_space
#          .state_time_auxiliary_space
#          .state_bounding_box
# domain = [state_space, time_range]

# LabelledEnclosure.bounding_box                     range(state) + range(time)
#                  .dimension                        dim(state) + dim(time)
#                  .state_set
#                  .state_auxiliary_set
#                  .state_time_auxiliary_set

# ValidatedConstrainedImageSet.adjoin_outer_approximation_to
#                             .affine_approximation
#                             .affine_over_approximation
#                             .bounding_box
#                             .dimension
#                             .domain                             range(state) + range(time)
#                             .function                           state function
#                             .outer_approximation                (Ariadne::Grid, int) -> Ariadne::GridTreePaving


class EvolutionState(Enum):
    NONE = auto(),
    MISSING = auto(),
    ERROR = auto(),
    LOADING = auto(),
    LOADED = auto(),
    SAVING = auto(),
    SAVED = auto()


class PersistenceManager(object):
    orbit_dump_filename = "orbit.pkl"
    state = EvolutionState.NONE
    last_error = ''
    
    _orbit = None
    
    _all_variables = []
    all_variables_names = []
    polytopes = None
    
    def __init__(self, system):
        self.system = system
    
    def load_orbit(self):
        if os.path.isfile(self.orbit_dump_filename):
            print('Loading from file...', end='')
            self.state = EvolutionState.LOADING
            self.last_error = ''
            try:
                with open(self.orbit_dump_filename, "rb") as f:
                    dump = pickle.load(f)
                self.all_variables_names = dump['variables']
                self.polytopes = dump['polytopes']
                print('done')
                self.state = EvolutionState.LOADED
                self.last_error = ''
            except Exception as ex:
                print('ERROR! dump file could not be opened, keeping current trajectory')
                self.state = EvolutionState.ERROR
                self.last_error = ex
        else:
            print('ERROR! dump file not found, keeping current trajectory')
            self.state = EvolutionState.MISSING
            self.last_error = ''
    
    def save_orbit(self):
        data = {
            'variables': self.all_variables_names,
            'polytopes': self.polytopes
        }
        self.state = EvolutionState.SAVING
        self.last_error = ''
        try:
            with open(self.orbit_dump_filename, "wb") as f:
                pickle.dump(data, f)
            self.state = EvolutionState.SAVED
        except Exception as ex:
            self.state = EvolutionState.ERROR
            self.last_error = ex
    
    def clear_orbit(self):
        if os.path.isfile(self.orbit_dump_filename):
            print('Clearing file...', end='')
            os.unlink(self.orbit_dump_filename)
            print('done')
        else:
            print('WARNING! dump file not found')
        self.state = EvolutionState.MISSING
        self.last_error = ''
    
    def run_evolution(self, initial_set, final_time):
        evolver = ari.GeneralHybridEvolver(self.system)
        # set the evolver configuration
        # TODO add a way to set these parameters
        # evolver.configuration().set_enable_reconditioning(self: ari.GeneralHybridEvolverConfiguration, arg0: bool) -> None
        # evolver.configuration().set_enable_subdivisions(self: ari.GeneralHybridEvolverConfiguration, arg0: bool) -> None
        # evolver.configuration().set_maximum_enclosure_radius(self: ari.GeneralHybridEvolverConfiguration, arg0: ari.ApproximateDouble) -> None
        # evolver.configuration().set_maximum_spacial_error(self: ari.GeneralHybridEvolverConfiguration, arg0: ari.ApproximateDouble) -> None
        # evolver.configuration().set_maximum_step_size(self: ari.GeneralHybridEvolverConfiguration, arg0: ari.ApproximateDouble) -> None
        evolver.configuration().set_maximum_enclosure_radius(3.0)
        evolver.configuration().set_maximum_step_size(0.25)
        orbit = evolver.orbit(initial_set, ari.HybridTerminationCriterion(final_time), ari.Semantics.UPPER)
        orbit_reach = orbit.reach()
        
        # FIXME GERETTI: there's no way of explicitly getting the list of all the variables, but this might be enough
        self._all_variables = [orbit_reach[0].state_time_auxiliary_space().variable(i) for i in range(orbit_reach[0].state_time_auxiliary_space().dimension())]
        self.all_variables_names = [str(v) for v in self._all_variables]
        self._orbit = orbit
    
    def extract_projections(self, var_list=None):
        
        if not var_list:
            var_list = self._all_variables
        
        orbit_reach = self._orbit.reach()
        
        polytopes = []
        # projections are 2D, so we need a list of them which will later be joint together
        axes = [ari.Variables2d(var_list[i * 2], var_list[i * 2 + 1]) for i in range((len(var_list) - 1) // 2)] \
               + [ari.Variables2d(var_list[len(var_list) - 2], var_list[len(var_list) - 1])]
        for instant, encl in enumerate(orbit_reach):
            # since state/auxiliary variables can change during the evolution, we project them in the required order based on the axes we want
            prj = [ari.projection(encl.state_time_auxiliary_space(), a) for a in axes]
            # we extract the polytope points accordingly to the axes we want
            polytope_points_2d = [encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(p.i, p.j) for p in prj]
            # avoid punctual polytopes
            # FIXME GERETTI: for some reason, projections output polytopes inconsistent in points number
            min_prj = min([len(axes_points_2d) for axes_points_2d in polytope_points_2d])
            if min_prj >= 2:
                # get actual coordinates of the vertices of the polytope
                polytope = {
                    'loc': str(encl.location()),
                    'time': float(str(encl.time_range().upper_bound()))}
                for var_i, axes_points_2d in enumerate(polytope_points_2d[:-1]):
                    polytope[str(var_list[var_i * 2])] = [p.x for p in axes_points_2d[:min_prj]] + [axes_points_2d[0].x]
                    polytope[str(var_list[var_i * 2 + 1])] = [p.y for p in axes_points_2d[:min_prj]] + [axes_points_2d[0].y]
                last_axes_points_2d = polytope_points_2d[-1]
                if len(var_list) % 2 == 0:
                    polytope[str(var_list[-2])] = [p.x for p in last_axes_points_2d[:min_prj]] + [last_axes_points_2d[0].x]
                    polytope[str(var_list[-1])] = [p.y for p in last_axes_points_2d[:min_prj]] + [last_axes_points_2d[0].y]
                else:
                    # odd number of variables, x values will be redundant
                    polytope[str(var_list[-1])] = [p.y for p in last_axes_points_2d[:min_prj]] + [last_axes_points_2d[0].y]
                polytopes.append(polytope)
            else:
                print(f'WARNING: instant {instant} polytope has less than 2 vertices', file=sys.stderr)
        
        df = pd.DataFrame(polytopes)
        df['polytope_id'] = df.index + 1
        df = df.explode([str(var) for var in var_list])
        self.polytopes = df


class App(object):
    hybrid_system = None
    automatons = []
    automatons_analysis = {}
    
    configurable_automatons = []
    configurable_variables = []
    
    def __init__(self, system):
        self.hybrid_system = system
        # FIXME GERETTI: CompositeHybridAutomaton is not iterable, but I need this list programmatically
        self.automatons = ['controller', 'tank', 'valve']
        
        # create graphs of the automatons
        self._batch_analyze()
        
        self.configurable_automatons = [automaton_name for automaton_name, automaton_info in self.automatons_analysis.items() if automaton_info['configurable']]
        # FIXME GERETTI: need a way to get the set of dynamic variables at stake in a certain location
        self.configurable_variables = sorted(set([var for automaton_info in self.automatons_analysis.values() for var in automaton_info['dynamics'].values()]))
        dynamics = {
            'controller': {
                'falling': [],
                'rising': []
            },
            'tank': {
                '_': ['height']
            },
            'valve': {
                'closed': [],
                'closing': ['aperture'],
                'opened': [],
                'opening': ['aperture']
            }
        }
        self.configurable_variables = ['height']
        
        self.persistence = PersistenceManager(self.hybrid_system)
    
    def _analyze_automaton(self, automaton: ari.HybridAutomaton, name=None):
        def explode_location(location):
            # if empty location, the system has one location only, thus the 'no_name' and the '--' location
            return tuple((str(location)[1:-1]).split('|')) if '|' in str(location) else (name if name else 'no_name', '--')
        
        def binding_safe_get(pybind_fun_call):
            try:
                return pybind_fun_call()
            except RuntimeError:
                return None
        
        locations = dict(enumerate(automaton.locations()))
        
        # FIXME GERETTI: get automaton name
        model_name = explode_location(list(locations.values())[0])[0]
        
        info = {
            'name': model_name,
            'configurable': True,
            'locations': [],
            'dynamics': {},
            'nodes': {},
            'edges': {}
        }
        
        edge_count = 0
        for i, loc in locations.items():
            # get location info
            location_name = explode_location(loc)[1]
            # FIXME GERETTI: get the variables' names, which get print but can't be retrieved
            # FIXME GERETTI: get algebraic function
            dynamic_function = binding_safe_get(lambda: automaton.dynamic_function(loc))
            algebraic_function = None  # binding_safe_get(lambda: system.algebraic_function(loc))
            info['nodes'][f'node{i}'] = {
                'data': {
                    'id': f'{location_name}',
                    'label': f'{location_name}',
                    'dynamic_function': f'{dynamic_function}',
                    'algebraic_function': f'{algebraic_function}'
                }
            }
            info['locations'].append(location_name)
            info['dynamics'][location_name] = None  # FIXME GERETTI: get variable of dynamic function, if existing
            
            # possible events when in this location
            for event in automaton.events(loc):
                # get transaction info
                target = automaton.target(loc, event)
                info['edges'][f'edge{edge_count}'] = {
                    'data': {
                        'source': explode_location(loc)[1],
                        'target': explode_location(target)[1],
                        'label': f"{event}",
                        # when this event is output in this location, then we know its kind
                        'event_kind': binding_safe_get(lambda: automaton.event_kind(loc, event).name),
                        # when this event is not an invariant (es. PERMISSIVE), then it has a triggering guard
                        'guard_function': str(binding_safe_get(lambda: automaton.guard_function(loc, event))),
                        # FIXME GERETTI: get invariant function
                        # 'invariant_function': safe_get(lambda: system.invariant_function(loc, event)),
                        'reset_fun': str(binding_safe_get(lambda: automaton.reset_function(loc, event)))
                    }
                }
                edge_count += 1
        
        # if we just have one location, then we can't choose the initial one later on
        if len(info['nodes']) <= 1:
            info['configurable'] = False
        
        return info
    
    def _batch_analyze(self):
        # FIXME GERETTI: as above, can iterate self.hybrid_system
        for automaton_name in self.automatons:
            # get automaton of interest
            automaton = getattr(example_system, f'get_{automaton_name}')()
            automaton_graph = self._analyze_automaton(automaton, name=automaton_name)
            self.automatons_analysis[automaton_graph['name']] = automaton_graph
    
    def get_automaton_graph(self, selected_automaton):
        nodes = [data for _, data in self.automatons_analysis[selected_automaton]['nodes'].items()]
        edges = [data for _, data in self.automatons_analysis[selected_automaton]['edges'].items()]
        return nodes + edges


app_logic = App(example_system.get_system())

# build dashboard
app = dash.Dash(__name__,
                external_stylesheets=[
                    'https://codepen.io/chriddyp/pen/bWLwgP.css'
                ],
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1"}
                ])
app.layout = html.Div([
    html.Div(id='placeholder', style={'display': 'none'}),
    html.H1('Ariadne Dashboard'),
    html.Div([
        html.H4('Evolver Configurator'),
        html.Div([
            html.Div([
                core.Loading(
                    id="loading-automaton",
                    type="default",
                    children=[
                        html.Div([
                            html.H6('Automaton selector'),
                            core.ConfirmDialog(
                                id='system-import-not-implemented',
                                message='This feature is currently not implemented',
                            ),
                            html.Div([
                                html.Button('Import hybrid system', id='system-import', n_clicks=0)
                            ],
                                style={
                                    'margin-bottom': '1%',
                                    'display': 'flex',
                                    'flex-direction': 'row',
                                    'place-content': 'space-around',
                                    'justify-content': 'space-around',
                                    'align-content': 'center',
                                    'align-items': 'center'
                                }
                            ),
                            core.Dropdown(
                                id='automaton-selector',
                                options=[{'label': automaton_name, 'value': automaton_name} for automaton_name in sorted(app_logic.automatons)]
                            ),
                            cyto.Cytoscape(
                                id='automaton-graph',
                                layout={
                                    'name': 'circle'
                                },
                                elements=[],
                                stylesheet=[
                                    {
                                        'selector': 'node',
                                        'style': {
                                            'label': 'data(label)',
                                            # FIXME node size programmatically
                                            'min-width': 'label',
                                            'width': 'label',
                                            'min-height': 'label',
                                            'height': 'label',
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
                                            'target-arrow-shape': 'triangle',
                                            'text-rotation': 'autorotate'
                                        }
                                    }
                                ],
                                responsive=True,
                                style={'height': '65vh'}
                            )
                        ])
                    ]
                )
            ],
                style={'width': '49%', 'display': 'inline-block'}
            ),
            html.Div([
                core.Loading(
                    id='loading-evolution',
                    type="default",
                    children=[
                        # initial conditions
                        html.Div(
                            [html.H6('Initial Location')]
                            + [
                                core.Dropdown(
                                    id={
                                        'type': 'config-init-automaton-location',
                                        'index': automaton_name
                                    },
                                    placeholder=f'Choose \"{automaton_name}\" automaton initial location',
                                    options=[{'label': f'{automaton_name}|{location}', 'value': location}
                                             for location in sorted(app_logic.automatons_analysis[automaton_name]['locations'])],
                                    style={'margin-bottom': '1%'}
                                )
                                for automaton_name in sorted(app_logic.configurable_automatons)]
                            + [
                                item for var_selector in [
                                    [
                                        html.H6(f'{variable_name.capitalize()}'),
                                        html.Div([
                                            core.Checklist(
                                                id={
                                                    'type': 'config-init-variable-is_range',
                                                    'index': variable_name
                                                },
                                                options=[{'label': 'Range', 'value': 'true'}],
                                                value=[],
                                                labelStyle={'display': 'inline-block'},
                                                style={'width': '15%', 'display': 'inline-block'}
                                            ),
                                            core.Checklist(
                                                id={
                                                    'type': 'config-init-variable-include_lower',
                                                    'index': variable_name
                                                },
                                                options=[{'label': '', 'value': 'true'}],
                                                value=[],
                                                labelStyle={'display': 'inline-block'},
                                                style={'width': '5%', 'text-align': 'center'}
                                            ),
                                            core.Input(
                                                id={
                                                    'type': 'config-init-variable-lower',
                                                    'index': variable_name
                                                },
                                                type='number',
                                                step=0.1,
                                                placeholder='Lower bound',
                                                style={'width': '37.5%'}
                                            ),
                                            core.Input(
                                                id={
                                                    'type': 'config-init-variable-upper',
                                                    'index': variable_name
                                                },
                                                type='number',
                                                step=0.1,
                                                placeholder='Upper bound',
                                                style={'width': '37.5%'}
                                            ),
                                            core.Checklist(
                                                id={
                                                    'type': 'config-init-variable-include_upper',
                                                    'index': variable_name
                                                },
                                                options=[{'label': '', 'value': 'true'}],
                                                value=[],
                                                labelStyle={'display': 'inline-block'},
                                                style={'width': '5%', 'text-align': 'center'}
                                            )
                                        ],
                                            style={
                                                'margin-bottom': '1%',
                                                'display': 'flex',
                                                'flex-direction': 'row',
                                                'place-content': 'space-around',
                                                'justify-content': 'space-around',
                                                'align-content': 'center',
                                                'align-items': 'center'
                                            }
                                        )
                                    ] for variable_name in sorted(app_logic.configurable_variables)]
                                for item in var_selector]
                        ),
                        # termination conditions
                        html.Div([
                            html.Div([
                                html.H6('Final Time'),
                                core.Input(
                                    id='config-final-time',
                                    type='number',
                                    min=0.0,
                                    step=0.1,
                                    placeholder='Set final time'
                                )
                            ],
                                style={'width': '49%', 'display': 'inline-block'}
                            ),
                            html.Div([
                                html.H6('Maximum Transitions'),
                                core.Input(
                                    id='config-max-transitions',
                                    type='number',
                                    placeholder='Set maximum transitions'
                                )
                            ],
                                style={'width': '49%', 'display': 'inline-block'}
                            ),
                        ],
                            style={'display': 'flex', 'justify-content': 'space-between', 'margin-bottom': '1%'}
                        ),
                        # run/clean evolution buttons
                        html.Div([
                            html.Button('Run evolution', id='run-evolution', n_clicks=0),
                            html.Button('Clear evolution', id='clear-evolution', n_clicks=0)
                        ],
                            style={
                                'margin-bottom': '1%',
                                'display': 'flex',
                                'flex-direction': 'row',
                                'place-content': 'space-around',
                                'justify-content': 'space-around',
                                'align-content': 'center',
                                'align-items': 'center'
                            }
                        ),
                        html.Div([
                            html.H5(
                                '',
                                id='run-state',
                                style={
                                    'text-align': 'center',
                                    'text-transform': 'uppercase'
                                }
                            ),
                            html.Plaintext(
                                '',
                                id='run-error',
                                style={
                                    'font-family': 'monospace',
                                    'padding-left': '10pt',
                                    'padding-right': '10pt',
                                    # 'padding-bottom': '6pt'
                                }
                            )
                        ],
                            style={
                                'background-color': '#eeeeee',
                                'border-radius': '10pt',
                                'margin-top': '2%'
                            }
                        )
                    ]
                )
            ],
                style={'width': '49%', 'display': 'inline-block'}
            )
        ],
            style={'display': 'flex', 'justify-content': 'space-between'}
        )
    ],
        style={'width': '49%', 'float': 'left', 'display': 'inline-block'}
    ),
    html.Div(
        id='trajectory-plotter',
        className='unavailable',
        children=[
            html.H4('Trajectory Plotter'),
            html.Div([
                # axes selection
                html.Div([
                    html.Div([
                        html.H6('X axis'),
                        core.Dropdown(
                            id='x-variable',
                            options=[])
                    ],
                        style={'width': '33%', 'display': 'inline-block'}
                    ),
                    html.Div([
                        html.H6('Y axis'),
                        core.Dropdown(
                            id='y-variable',
                            options=[])
                    ],
                        style={'width': '33%', 'display': 'inline-block'}
                    ),
                    html.Div([
                        html.H6('Z axis'),
                        core.Dropdown(
                            id='z-variable',
                            options=[])
                    ],
                        style={'width': '33%', 'display': 'inline-block'}
                    ),
                ],
                    style={'display': 'flex', 'justify-content': 'space-between'}
                ),
                # time selection
                html.Div([
                    html.H6('Time'),
                    core.RangeSlider(
                        id='time-slider',
                        min=0,
                        max=0,
                        value=[0, 0],
                        marks={},
                        tooltip={
                            'always_visible': True,
                            'placement': 'bottom'
                        },
                        step=0,
                        dots=False,
                        allowCross=False
                    )
                ]),
            ]),
            core.Loading(
                id="loading-graph",
                type="default",
                children=[
                    core.Graph(
                        id='trajectory-graph',
                        figure=px.line(),
                        style={'height': '65vh'}
                    )
                ]
            )
        ],
        style={'width': '49%', 'float': 'right', 'display': 'inline-block'}
    )
])


@app.callback(
    Output('system-import-not-implemented', 'displayed'),
    Input('system-import', 'n_clicks'),
    prevent_initial_call=True
)
def import_system(_):
    return True


@app.callback(
    Output('run-state', 'children'),
    Output('run-error', 'children'),
    Input('run-evolution', 'n_clicks'),
    Input('clear-evolution', 'n_clicks'),
    State('config-final-time', 'value'),
    State('config-max-transitions', 'value'),
    State({'type': 'config-init-automaton-location', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-is_range', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-lower', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-upper', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-include_lower', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-include_upper', 'index': ALL}, 'value')
)
def run_system_evolution(_, __, final_time, max_transitions, locations, are_range, lower_bounds, upper_bounds, include_lowers, include_uppers):
    if not dash.callback_context.triggered:
        # load last run
        print("Reloading last trajectory")
        app_logic.persistence.load_orbit()
        if app_logic.persistence.state == EvolutionState.ERROR:
            return 'Error', f'{app_logic.persistence.last_error}'
        if app_logic.persistence.state == EvolutionState.MISSING:
            return 'Missing', ''
        elif app_logic.persistence.state == EvolutionState.LOADED:
            return 'Loaded', ''
        elif app_logic.persistence.state == EvolutionState.SAVED:
            return 'Saved', ''
    
    if dash.callback_context.triggered[0]['prop_id'].split('.')[0] == 'clear-evolution':
        app_logic.persistence.clear_orbit()
        return 'Missing', ''
    
    if final_time is None:
        return 'Missing parameters', 'Specify a valid final time'
    if max_transitions is None:
        return 'Missing parameters', 'Specify a maximum number of transitions'
    for automaton_name, automaton_location in zip(app_logic.configurable_automatons, locations):
        if automaton_location is None:
            return 'Missing parameters', f'Specify initial location for automaton \"{automaton_name}\"'
    for variable_name, r, l, u in zip(app_logic.configurable_variables, are_range, lower_bounds, upper_bounds):
        if r:
            if l is None:
                return 'Missing parameters', f'Specify lower bound for variable \"{variable_name}\"'
            if u is None:
                return 'Missing parameters', f'Specify upper bound for variable \"{variable_name}\"'
        else:
            if l is None:
                return 'Missing parameters', f'Specify value for variable \"{variable_name}\"'
    
    try:
        initial_location = {
            ari.StringVariable(automaton_name): ari.String(automaton_location)
            for automaton_name, automaton_location in zip(app_logic.configurable_automatons, locations)
        }
        initial_conditions = [
            variable == lower_bound
            if not is_range else
            (
                ari.dec(lower_bound) <= variable
                if include_lower else
                ari.dec(lower_bound) < variable  # FIXME GERETTI: this breaks Ariadne
            ) & (
                variable <= ari.dec(upper_bound)
                if include_upper else
                variable < ari.dec(upper_bound)  # FIXME GERETTI: this breaks Ariadne
            )
            for variable, is_range, lower_bound, upper_bound, include_lower, include_upper
            in zip([ari.RealVariable(var) for var in app_logic.configurable_variables], are_range, lower_bounds, upper_bounds, include_lowers, include_uppers)
        ]
        
        initial_set = ari.HybridBoundedConstraintSet(initial_location, initial_conditions)
        final_time = ari.HybridTime(ari.dec(float(final_time)), int(max_transitions))
    except Exception as ex:
        # PyAriadne errors, should never happen though...
        app_logic.persistence.state = EvolutionState.ERROR
        app_logic.persistence.last_error = ex
        return 'Error configuring!', f'{ex}'
    
    try:
        # let the system evolve over the given time
        print('Evolving...', end='')
        app_logic.persistence.run_evolution(initial_set, final_time)
        print('done')
    except Exception as ex:
        # PyAriadne errors, should never happen though...
        app_logic.persistence.state = EvolutionState.ERROR
        app_logic.persistence.last_error = ex
        return 'Error evolving!', f'{ex}'
    
    try:
        print('Extracting projections...', end='')
        app_logic.persistence.extract_projections()
        print('done')
    except Exception as ex:
        # should never happen, just in case...
        app_logic.persistence.state = EvolutionState.ERROR
        app_logic.persistence.last_error = ex
        return 'Error extracting!', f'{ex}'
    
    try:
        print('Dumping to file...', end='')
        app_logic.persistence.save_orbit()
        print('done')
    except Exception as ex:
        app_logic.persistence.state = EvolutionState.ERROR
        app_logic.persistence.last_error = ex
        return 'Error dumping!', f'{ex}'
    
    return 'Done', ''


@app.callback(
    Output('trajectory-plotter', 'className'),
    Output('x-variable', 'options'),
    Output('y-variable', 'options'),
    Output('z-variable', 'options'),
    Output('time-slider', 'max'),
    Output('time-slider', 'step'),
    Output('time-slider', 'value'),
    Input('run-state', 'children')
)
def enable_trajectory_plotter(_):
    if app_logic.persistence.state == EvolutionState.LOADED \
            or app_logic.persistence.state == EvolutionState.SAVED:
        options = [{'label': i, 'value': i} for i in app_logic.persistence.all_variables_names]
        val = app_logic.persistence.polytopes['time'].max()
        return 'available', options, options, options, val, val / 100, [0, val]
    else:
        return 'unavailable', [], [], [], 0, 0, [0, 0]


@app.callback(
    Output({'type': 'config-init-variable-lower', 'index': MATCH}, 'placeholder'),
    Output({'type': 'config-init-variable-upper', 'index': MATCH}, 'className'),
    Output({'type': 'config-init-variable-include_lower', 'index': MATCH}, 'className'),
    Output({'type': 'config-init-variable-include_upper', 'index': MATCH}, 'className'),
    Input({'type': 'config-init-variable-is_range', 'index': MATCH}, 'value')
)
def update_variable_initializer(is_range):
    if not is_range:
        return 'Value', 'disabled', 'disabled', 'disabled'
    return 'Lower bound', '', '', ''


@app.callback(
    Output('automaton-graph', 'elements'),
    Input('automaton-selector', 'value'),
    prevent_initial_call=True
)
def update_automaton_graph(selected_automaton):
    if selected_automaton is None:
        raise dash.exceptions.PreventUpdate
    return app_logic.get_automaton_graph(selected_automaton)


@app.callback(
    Output('trajectory-graph', 'figure'),
    Input('time-slider', 'value'),
    Input('x-variable', 'value'),
    Input('y-variable', 'value'),
    Input('z-variable', 'value'),
    prevent_initial_call=True
)
def update_trajectory_plot(selected_time, var_x, var_y, var_z):
    # TODO do I need to plot 3D meshes or are polylines just fine?
    # fig = go.Figure(data=[
    #     go.Mesh3d(x=p['t'], y=p['height'], z=p['aperture'],
    #               alphahull=0, opacity=0.75, color='cyan')
    #     for p in orbit_polytopes[:50]])
    
    if var_x is None or var_y is None:
        raise dash.exceptions.PreventUpdate
    else:
        filtered_df = app_logic.persistence.polytopes[
            (selected_time[0] <= app_logic.persistence.polytopes.time) & (app_logic.persistence.polytopes.time <= selected_time[1])]
        if var_z is None:
            fig = px.line(filtered_df, x=var_x, y=var_y,
                          color="loc", line_group="polytope_id")
        else:
            fig = px.line_3d(filtered_df, x=var_x, y=var_y, z=var_z,
                             color="loc", line_group="polytope_id")
    fig.update_layout(transition_duration=500)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
