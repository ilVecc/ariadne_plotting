#!/usr/bin/python3

import yaml
from pyariadne import *
import example_system


def serialize(hybrid_enclosure_list_set):
    
    def HybridEnclosure_representer(dumper, data):
        location = data.location()
        continuous_set = data.continuous_set()
        return dumper.represent_scalar(u'!HybridEnclosure', u'%s' % data)

    def HybridEnclosure_constructor(loader, node):
        value = loader.construct_scalar(node)
        variable, state = value[1:-1].split("|")
        return DiscreteLocation({StringVariable(variable): state})

    yaml.add_representer(HybridEnclosure, HybridEnclosure_representer)
    yaml.add_constructor("!HybridEnclosure", HybridEnclosure_constructor)
    
    hybrid_enclosure = hybrid_enclosure_list_set[0]
    yamlData = yaml.dump(hybrid_enclosure)
    print(yamlData)
    
    yaml_rising = yaml.load(yamlData, Loader=yaml.FullLoader)
    print(yaml_rising)


if __name__ == '__main__':
    # Get the system, the initial set and the final time
    system = example_system.get_system()
    initial_set = example_system.get_initial_set()
    final_time = example_system.get_final_time()
    
    evolver = example_system.create_evolver(system)
    orbit = example_system.compute_evolution(evolver, initial_set, final_time)
    orbit_reach = orbit.reach()
    
    serialize(orbit_reach)
