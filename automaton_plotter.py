import dash
import dash_html_components as html

from backend.plotting_backend import analyze_automaton, build_cytoscape_graph, plot_automaton
from systems import tutorial_system

if __name__ == '__main__':
    # build an automaton as usual
    automaton = tutorial_system.get_valve()
    
    # analyse and get graph elements
    automaton_analysis = analyze_automaton(automaton)
    automaton_graph_elements = build_cytoscape_graph(automaton_analysis)
    # use Dash-Cytoscape to plot the automaton
    graph = plot_automaton(automaton_graph_elements)
    setattr(graph, 'style', {'width': '100%', 'height': '500px'})
    
    app = dash.Dash(__name__,
                    external_stylesheets=[
                        'https://codepen.io/chriddyp/pen/bWLwgP.css'
                    ],
                    meta_tags=[
                        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
                    ])
    
    app.layout = html.Div([
        graph
    ])
    app.run_server(debug=False)
