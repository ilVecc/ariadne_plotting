#!/usr/bin/python3

import yaml
from pyariadne import *
import example_system


def serialize(hybrid_enclosure_list_set):
    
    def HybridEnclosureListSet_representer(dumper, data):
        sequence = [i for i in data]
        return dumper.represent_sequence(u'!HybridEnclosureListSet', sequence)
    
    def HybridEnclosure_representer(dumper, data):
        mapping = {
            'location': data.location(),
            'continuous_set': data.continuous_set()
        }
        return dumper.represent_mapping(u'!HybridEnclosure', mapping)

    # def HybridEnclosure_constructor(loader, node):
    #     value = loader.construct_scalar(node)
    #     variable, state = value[1:-1].split("|")
    #     return DiscreteLocation({StringVariable(variable): state})

    def DiscreteLocation_representer(dumper, data):
        return dumper.represent_scalar(u'!DiscreteLocation', u'%s' % data)

    # def DiscreteLocation_constructor(loader, node):
    #     value = loader.construct_scalar(node)
    #     variable, state = value[1:-1].split("|")
    #     return DiscreteLocation({StringVariable(variable): state})
    
    # TODO must be represented as a multidimensional set, but I have no idea how, this is broken now
    def LabelledEnclosure_representer(dumper, data):
        mapping = {
            'state_time_auxiliary_set': data.state_time_auxiliary_set()
        }
        return dumper.represent_mapping(u'!LabelledEnclosure', mapping)

    # TODO probably don't need this Euclidean space
    def ValidatedConstrainedImageSet_representer(dumper, data):
        mapping = {
            'affine_over_approximation': data.affine_over_approximation()
        }
        return dumper.represent_mapping(u'!ValidatedConstrainedImageSet', mapping)

    # TODO probably don't need this 2D projection
    def ValidatedAffineConstrainedImageSet_representer(dumper, data):
    
        # axes = Variables2d(var1, var2)
        # for encl in orbit_reach:
        #     prj = projection(encl.state_time_auxiliary_space(), axes)
        #     points = encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(prj.i, prj.j)
        #     # do not plot polytopes with less then 3 vertices
        #     if len(points) > 2:
        #         x = [p.x for p in points]
        #         x.append(x[0])
        #         y = [p.y for p in points]
        #         y.append(y[0])
        #         plt.plot(x, y)
        
        mapping = {
            'list': '' #data.boundary(1, 0)
        }
        return dumper.represent_sequence(u'!ValidatedAffineConstrainedImageSet', mapping)
    
    yaml.add_representer(HybridEnclosureListSet, HybridEnclosureListSet_representer)
    yaml.add_representer(HybridEnclosure, HybridEnclosure_representer)
    yaml.add_representer(DiscreteLocation, DiscreteLocation_representer)
    yaml.add_representer(LabelledEnclosure, LabelledEnclosure_representer)
    yaml.add_representer(ValidatedConstrainedImageSet, ValidatedConstrainedImageSet_representer)
    yaml.add_representer(ValidatedAffineConstrainedImageSet, ValidatedAffineConstrainedImageSet_representer)

    # yaml.add_constructor("!HybridEnclosure", HybridEnclosure_constructor)
    # yaml.add_constructor("!DiscreteLocation", DiscreteLocation_constructor)

    hybrid_enclosure = hybrid_enclosure_list_set
    yamlData = yaml.dump(hybrid_enclosure)
    with open('dump.yaml', 'w') as f:
        f.write(yamlData)
    
    # yaml_rising = yaml.load(yamlData, Loader=yaml.FullLoader)
    # print(yaml_rising)


if __name__ == '__main__':
    
    controller = example_system.get_controller()
    
    # Get the system, the initial set and the final time
    system = example_system.get_system()
    initial_set = example_system.get_initial_set()
    final_time = example_system.get_final_time()
    
    evolver = example_system.create_evolver(system)
    orbit = example_system.compute_evolution(evolver, initial_set, final_time)
    orbit_reach = orbit.reach()
    
    serialize(orbit_reach)
