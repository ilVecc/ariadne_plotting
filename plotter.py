#!/usr/bin/python3

from pyariadne import *
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import example_system


def plot(orbit_reach, var1, var2):
    axes = Variables2d(var1, var2)
    for encl in orbit_reach:
        prj = projection(encl.state_time_auxiliary_space(), axes)
        points = encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(prj.i, prj.j)
        # do not plot polytopes with less then 3 vertices
        if len(points) >= 2:
            x = [p.x for p in points]
            x.append(x[0])
            y = [p.y for p in points]
            y.append(y[0])
            plt.plot(x, y)
        else:
            print('WARNING: the polytope has less than 2 vertices')
    plt.show()


# encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(xcoord, ycoord)
# HybridEnclosure -> LabelledEnclosure -> ValidatedConstrainedImageSet -> ValidatedAffineConstrainedImageSet -> List<Point2d>

# HybridEnclosure: coppia locazione-insieme
# LabelledEnclosure: insieme con variabili simboliche
# ValidatedConstrainedImageSet: insieme su spazio euclideo n-dimensionale
# ValidatedAffineConstrainedImageSet: proiezione 2-dimensionale dell'insieme su due variabili (es. tempo/apertura) le variabili sono  in ordine
#                                     1) variabili differenziali in ordine alfabetico,
#                                     2) tempo,
#                                     3) variabili algebriche in ordine alfabetico
# List<Point2d>: date le coordinate del politopo, lista dei vertici del politopo

# Enclosure::bounding_box
# Enclosure::state_set
# Enclosure::state_auxiliary_set
# Enclosure::state_time_auxiliary_set

# LabelledEnclosure<Enclosure>::bounding_box

# ValidatedConstrainedImageSet::domain
# ValidatedConstrainedImageSet::function
# ValidatedConstrainedImageSet::constraint
# ValidatedConstrainedImageSet::number_of_parameters
# ValidatedConstrainedImageSet::number_of_constraints
# ValidatedConstrainedImageSet::apply
# ValidatedConstrainedImageSet::new_space_constraint
# ValidatedConstrainedImageSet::new_parameter_constraint
# ValidatedConstrainedImageSet::outer_approximation
# ValidatedConstrainedImageSet::affine_approximation
# ValidatedConstrainedImageSet::affine_over_approximation
# ValidatedConstrainedImageSet::adjoin_outer_approximation_to
# ValidatedConstrainedImageSet::bounding_box
# ValidatedConstrainedImageSet::inside
# ValidatedConstrainedImageSet::separated
# ValidatedConstrainedImageSet::overlaps

# ValidatedAffineConstrainedImageSet::new_parameter_constraint
# ValidatedAffineConstrainedImageSet::new_constraint
# ValidatedAffineConstrainedImageSet::dimension
# ValidatedAffineConstrainedImageSet::is_bounded
# ValidatedAffineConstrainedImageSet::is_empty
# ValidatedAffineConstrainedImageSet::bounding_box
# ValidatedAffineConstrainedImageSet::separated
# ValidatedAffineConstrainedImageSet::adjoin_outer_approximation_to
# ValidatedAffineConstrainedImageSet::outer_approximation
# ValidatedAffineConstrainedImageSet::boundary


def batch_matplotlib_plot(hybrid_enclosure_list_set):
    t = RealVariable("t")
    height = RealVariable("height")
    aperture = RealVariable("aperture")
    
    plot(hybrid_enclosure_list_set, t, aperture)
    plot(hybrid_enclosure_list_set, t, height)
    plot(hybrid_enclosure_list_set, height, aperture)


def batch_plotly_plot(hybrid_enclosure_list_set):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[1.5, 3],
        y=[2.5, 2.5],
        text=["Rectangle reference to the plot",
              "Rectangle reference to the axes"],
        mode="text",
    ))
    fig.show()


if __name__ == '__main__':
    # Get the system, the initial set and the final time
    system = example_system.get_system()
    initial_set = example_system.get_initial_set()
    final_time = example_system.get_final_time()
    
    evolver = example_system.create_evolver(system)
    orbit = example_system.compute_evolution(evolver, initial_set, final_time)
    orbit_reach = orbit.reach()
    
    batch_matplotlib_plot(orbit_reach)
    # batch_plotly_plot(orbit_reach)
