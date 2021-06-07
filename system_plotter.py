

# !/usr/bin/python3

import yaml
from pyariadne import *
import example_system


def make_graph(system):
    
    locations = dict(enumerate(system.locations()))
    graph_nodes = {i: (str(loc)[1:-1]).split('|')[1] for i, loc in locations.items()}
    graph_trans = {}

    for i, loc in locations.items():
        events = system.events(loc)
        for event in events:
            dynamic_function = system.dynamic_function(loc)
            event_kind = system.event_kind(loc, event)
            reset_function = system.reset_function(loc, event)
            event_type = system.guard_function(loc, event)
            graph_trans[i] = {'cond': str(event),
                              'to': event_type}
    

if __name__ == '__main__':
    controller = example_system.get_valve()
    make_graph(controller)
