#!/usr/bin/python3

__version__ = '1.0'
__all__ = [
    'launch'
]

import re
from enum import Enum, auto

import dash
import dash_core_components as core
import dash_html_components as html
import plotly.express as px
import pyariadne as ari
from dash.dependencies import Output, Input, State, MATCH, ALL

from backend.plotting_backend import plot_trajectory, orbit_to_dataframe, plot_automaton, analyze_automaton, build_cytoscape_graph, get_all_variables
from systems import tutorial_system


class EvolutionState(Enum):
    NONE = auto(),
    MISSING = auto(),
    ERROR = auto(),
    LOADING = auto(),
    LOADED = auto(),
    SAVING = auto(),
    READY = auto(),
    DONE = auto()


class AppLogic(object):
    hybrid_system = None
    all_variables_names = []
    _orbit = None
    
    automatons_analysis = {}
    automatons_graphs = {}
    
    configurable_automatons = []
    configurable_variables = []
    
    current_variables = []
    state = EvolutionState.NONE
    polytopes = None
    
    def __init__(self, system):
        self.hybrid_system = system
        self.all_variables_names = get_all_variables(system)
        
        # extract info and create graphs of the automatons
        self._batch_analyze_automaton()
        self._batch_build_graph()
        
        # if we just have one location, then we can't choose the initial one later on
        self.configurable_automatons = sorted([
            automaton_info['name']
            for automaton_info in self.automatons_analysis.values() if len(automaton_info['locations']) > 1
        ])
        # in order to set the initial conditions we extract, for each location of each automaton, the dynamic variables
        self.configurable_variables = {
            automaton_name: {
                location_name: [
                    var
                    for item in [re.findall(r"dot\((.*?)\)", str(assignment)) for assignment in location_info['dynamic_assignments']]
                    for var in item
                ]
                for location_name, location_info in automaton_info['locations'].items()
            }
            for automaton_name, automaton_info in self.automatons_analysis.items()
        }
    
    def _batch_build_graph(self):
        self.automatons_graphs = {
            automaton_name: build_cytoscape_graph(automaton_info)
            for automaton_name, automaton_info in self.automatons_analysis.items()
        }
    
    def _batch_analyze_automaton(self):
        for automaton in self.hybrid_system:
            automaton_info = analyze_automaton(automaton)
            self.automatons_analysis[automaton_info['name']] = automaton_info
    
    def run_evolution(self, initial_set, final_time):
        # set the evolver configuration
        # TODO add a way to set these parameters
        # evolver.configuration().set_enable_reconditioning(self: ari.GeneralHybridEvolverConfiguration, arg0: bool) -> None
        # evolver.configuration().set_enable_subdivisions(self: ari.GeneralHybridEvolverConfiguration, arg0: bool) -> None
        # evolver.configuration().set_maximum_spacial_error(self: ari.GeneralHybridEvolverConfiguration, arg0: ari.ApproximateDouble) -> None
        evolver = ari.GeneralHybridEvolver(self.hybrid_system)
        evolver.configuration().set_maximum_enclosure_radius(3.0)
        evolver.configuration().set_maximum_step_size(0.25)
        self._orbit = evolver.orbit(initial_set, ari.HybridTerminationCriterion(final_time), ari.Semantics.UPPER)
    
    def extract_projections(self, var_list=None):
        if not var_list:
            var_list = self.all_variables_names
        orbit_reach = self._orbit.reach()
        self.polytopes = orbit_to_dataframe(orbit_reach=orbit_reach, var_list=var_list, collapse=(len(var_list) >= 3))
        return self.polytopes


# TODO add more conditions, not just BETWEEN and EQUAL_TO
def _make_variable_selector(variable_name):
    return \
        html.Div([
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
        ])


app_logic = AppLogic(tutorial_system.get_system())

# build dashboard
app = dash.Dash(__name__,
                external_stylesheets=[
                    'https://codepen.io/chriddyp/pen/bWLwgP.css'
                ],
                meta_tags=[
                    {"name": "viewport", "content": "width=device-width, initial-scale=1"}
                ])
app.layout = html.Div([
    html.H1('Ariadne Dashboard'),
    html.Div([
        html.Div([
            html.H4('Automaton Viewer'),
            html.Div([
                html.H6('Automaton selector'),
                core.Loading(
                    id="loading-system",
                    type="default",
                    fullscreen=True,
                    children=[
                        html.Div([
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
                                    'place-content': 'center space-around',
                                    'align-items': 'center'
                                }
                            )
                        ])
                    ]
                ),
                core.Loading(
                    id="loading-automaton-plot",
                    type="default",
                    children=[
                        core.Dropdown(
                            id='automaton-selector',
                            options=[{'label': automaton_name, 'value': automaton_name} for automaton_name in
                                     sorted(app_logic.automatons_analysis.keys())]
                        ),
                        html.Div(
                            id='automaton-plot',
                            children=[]
                        )
                    ]
                ),
                html.Div([
                    html.Plaintext(
                        id='automaton-plot-info-node',
                        children=[]
                    )
                ]),
                html.Div([
                    html.Plaintext(
                        id='automaton-plot-info-edge',
                        children=[]
                    )
                ])
            ])
        ],
            style={'width': '29%', 'display': 'inline-block'}
        ),
        html.Div([
            html.H4('Evolver Configurator'),
            core.Loading(
                id='loading-evolution',
                type="default",
                children=[
                    html.H6('Initial Location'),
                    # initial locations
                    html.Div([
                        core.Dropdown(
                            id={
                                'type': 'config-init-location',
                                'index': automaton_name
                            },
                            placeholder=f'Choose \"{automaton_name}\" automaton initial location',
                            options=[{'label': f'{automaton_name}|{location}', 'value': location}
                                     for location in sorted(app_logic.automatons_analysis[automaton_name]['locations'])],
                            style={'margin-bottom': '1%'}
                        )
                        for automaton_name in app_logic.configurable_automatons
                    ]),
                    # initial conditions in the selected locations
                    html.Div(
                        id='config-init-variables',
                        children=[]
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
                                placeholder='in seconds',
                                style={'width': '100%'}
                            )
                        ],
                            style={'width': '49%', 'display': 'inline-block'}
                        ),
                        html.Div([
                            html.H6('Max Transitions'),
                            core.Input(
                                id='config-max-transitions',
                                type='number',
                                min=0,
                                step=1,
                                placeholder='set number',
                                style={'width': '100%'}
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
                    # info/error log
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
                                'padding-right': '10pt'
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
            style={'width': '19%', 'display': 'inline-block'}
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
                                options=[]
                            )
                        ],
                            style={'width': '29%', 'display': 'inline-block'}
                        ),
                        html.Div([
                            html.H6('Y axis'),
                            core.Dropdown(
                                id='y-variable',
                                options=[]
                            )
                        ],
                            style={'width': '29%', 'display': 'inline-block'}
                        ),
                        html.Div([
                            html.H6('Z axis'),
                            core.Dropdown(
                                id='z-variable',
                                options=[]
                            )
                        ],
                            style={'width': '29%', 'display': 'inline-block'}
                        ),
                        core.Checklist(
                            id='use_mesh-selector',
                            options=[{'label': '3D Mesh', 'value': 'true'}],
                            value=[],
                            labelStyle={'display': 'inline-block'},
                            style={'width': '10%', 'text-align': 'center'}
                        )
                    ],
                        style={
                            'display': 'flex',
                            'flex-direction': 'row',
                            'place-content': 'center space-around',
                            'align-items': 'flex-end'
                        }
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
                            figure=px.line()
                        )
                    ]
                )
            ],
            style={'width': '49%', 'display': 'inline-block'}
        )
    ],
        style={
            'display': 'flex',
            'flex-direction': 'row',
            'place-content': 'center space-around',
            'align-items': 'stretch'
        }
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
    Output('config-init-variables', 'children'),
    Input({'type': 'config-init-location', 'index': ALL}, 'value')
)
def update_variable_selectors(locations):
    variables = \
        [
            # multi-locations automatons
            var
            for automaton_name, automaton_location in zip(app_logic.configurable_automatons, locations) if automaton_location
            for var in app_logic.configurable_variables[automaton_name][automaton_location]
        ] + [
            # single-location automatons
            var
            for automaton_name, automaton_locations in app_logic.configurable_variables.items() if len(automaton_locations) == 1
            for var in automaton_locations['--']
        ]
    app_logic.current_variables = sorted(list(set(variables)))
    return [_make_variable_selector(variable_name) for variable_name in app_logic.current_variables]


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
    Output('run-state', 'children'),
    Output('run-error', 'children'),
    Input('run-evolution', 'n_clicks'),
    Input('clear-evolution', 'n_clicks'),
    State('config-final-time', 'value'),
    State('config-max-transitions', 'value'),
    State({'type': 'config-init-location', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-is_range', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-lower', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-upper', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-include_lower', 'index': ALL}, 'value'),
    State({'type': 'config-init-variable-include_upper', 'index': ALL}, 'value')
)
def run_system_evolution(_, __, final_time, max_transitions, locations, are_range, lower_bounds, upper_bounds, include_lowers, include_uppers):
    if not dash.callback_context.triggered:
        print("WIP: reload last orbit as YAML")
        app_logic.state = EvolutionState.MISSING
        return 'Run the evolution to enable the trajectory plotter', ''
    
    if dash.callback_context.triggered[0]['prop_id'].split('.')[0] == 'clear-evolution':
        print("WIP: clear saved orbit")
        app_logic.state = EvolutionState.MISSING
        return 'Not implemented yet!', ''
    
    if final_time is None:
        return 'Missing parameters', 'Specify a valid final time'
    if max_transitions is None:
        return 'Missing parameters', 'Specify a maximum number of transitions'
    for automaton_name, automaton_location in zip(app_logic.configurable_automatons, locations):
        if automaton_location is None:
            return 'Missing parameters', f'Specify initial location for automaton \"{automaton_name}\"'
    for variable_name, r, l, u in zip(app_logic.current_variables, are_range, lower_bounds, upper_bounds):
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
            in zip([ari.RealVariable(var) for var in app_logic.current_variables], are_range, lower_bounds, upper_bounds, include_lowers, include_uppers)
        ]
        
        initial_set = ari.HybridBoundedConstraintSet(initial_location, initial_conditions)
        final_time = ari.HybridTime(ari.dec(float(final_time)), int(max_transitions))
        app_logic.state = EvolutionState.READY
    except Exception as ex:
        # PyAriadne errors, should never happen though...
        app_logic.state = EvolutionState.ERROR
        return 'Error configuring!', f'{ex}'
    
    try:
        # let the system evolve over the given time
        print('Evolving...', end='')
        app_logic.run_evolution(initial_set, final_time)
        app_logic.state = EvolutionState.DONE
        print('done')
    except Exception as ex:
        # PyAriadne errors, should never happen though...
        app_logic.state = EvolutionState.ERROR
        return 'Error evolving!', f'{ex}'
    
    print('WIP: save computed orbit as YAML')
    # try:
    #     print('Dumping to file...', end='')
    #     app_logic.save_orbit()
    #     print('done')
    # except Exception as ex:
    #     app_logic.state = EvolutionState.ERROR
    #     return 'Error dumping!', f'{ex}'
    
    return 'Done', ''


@app.callback(
    Output('trajectory-plotter', 'className'),
    Output('x-variable', 'options'),
    Output('y-variable', 'options'),
    Output('z-variable', 'options'),
    Input('run-state', 'children')
)
def enable_trajectory_plotter(_):
    if app_logic.state == EvolutionState.DONE:
        options = [{'label': i, 'value': i} for i in sorted(app_logic.all_variables_names)]
        return 'available', options, options, options
    else:
        return 'unavailable', [], [], []


@app.callback(
    Output('time-slider', 'max'),
    Output('time-slider', 'step'),
    Output('time-slider', 'value'),
    Input('x-variable', 'value'),
    Input('y-variable', 'value'),
    Input('z-variable', 'value'),
    prevent_initial_call=True
)
def update_time_slider(var_x, var_y, var_z):
    if var_x is None or var_y is None:
        raise dash.exceptions.PreventUpdate
    
    try:
        print('Extracting projections...', end='')
        var_list = [var_x, var_y] + ([var_z] if var_z else [])
        # TODO for some strange reason, asking the orbit here returns an exit(245)
        #  no idea why though, the trajectory_plotter.py works...
        app_logic.extract_projections(var_list)
        print('done')
    except Exception as ex:
        # should never happen, just in case...
        return 0, 0, [0, 0]
    
    range_max_val = app_logic.polytopes['_time'].max()
    return range_max_val, range_max_val / 100, [0, range_max_val]


@app.callback(
    Output('trajectory-graph', 'figure'),
    Input('time-slider', 'value'),
    Input('use_mesh-selector', 'value'),
    State('x-variable', 'value'),
    State('y-variable', 'value'),
    State('z-variable', 'value'),
    prevent_initial_call=True
)
def update_trajectory_plot(selected_time, use_mesh, var_x, var_y, var_z):
    polytopes_df = app_logic.polytopes[(selected_time[0] <= app_logic.polytopes['_time']) & (app_logic.polytopes['_time'] <= selected_time[1])]
    return plot_trajectory(polytopes_df, var_x, var_y, var_z, use_mesh)


@app.callback(
    Output('automaton-plot', 'children'),
    Input('automaton-selector', 'value'),
    prevent_initial_call=True
)
def update_automaton_graph(selected_automaton):
    if selected_automaton is None:
        raise dash.exceptions.PreventUpdate
    graph = app_logic.automatons_graphs[selected_automaton]
    cyto = plot_automaton(graph)
    setattr(cyto, 'style', {'width': '100%', 'height': '500px'})
    return cyto


# TODO display info when tapping the graph
# @app.callback(
#     Output('automaton-plot-info-node', 'children'),
#     Input('automaton-cytoscape', 'tapNodeData'),
#     prevent_initial_call=True
# )
# def display_automaton_graph_data(node_data):
#     return str(node_data)


# @app.callback(
#     Output('automaton-plot-info-edge', 'children'),
#     Input('automaton-cytoscape', 'tapEdgeData'),
#     prevent_initial_call=True
# )
# def display_automaton_graph_data(edge_data):
#     return str(edge_data)


def launch(debug=False):
    app.run_server(debug=debug)


if __name__ == '__main__':
    launch(debug=True)
