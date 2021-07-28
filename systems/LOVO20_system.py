#!/usr/bin/python3

from pyariadne import *


def get_automaton():
    x = RealVariable("x")
    y = RealVariable("y")
    cnt = RealVariable("cnt")
    
    alpha = RealConstant("alpha", 3)
    beta = RealConstant("beta", 3)
    gamma = RealConstant("gamma", 1)
    delta = RealConstant("delta", 1)
    radius = RealConstant("radius", dec(0.15))
    
    lotkavolterra = StringVariable("lotkavolterra")
    outside = String("outside")
    inside = String("inside")
    automaton = HybridAutomaton(lotkavolterra.name())
    
    enter = DiscreteEvent("enter")
    exit = DiscreteEvent("exit")
    
    cx = gamma / delta
    cy = alpha / beta
    
    automaton.new_mode({lotkavolterra: outside}, [dot(x) << alpha * x - beta * x * y, dot(y) << delta * x * y - gamma * y, dot(cnt) << 0])
    automaton.new_mode({lotkavolterra: inside}, [dot(x) << alpha * x - beta * x * y, dot(y) << delta * x * y - gamma * y, dot(cnt) << 1])
    
    automaton.new_transition({lotkavolterra: outside}, enter, {lotkavolterra: inside}, [next(x) << x, next(y) << y, next(cnt) << cnt],
                             sqr(x - cx) + sqr(y - cy) - sqr(radius) <= 0, IMPACT)
    automaton.new_transition({lotkavolterra: inside}, exit, {lotkavolterra: outside}, [next(x) << x, next(y) << y, next(cnt) << cnt],
                             sqr(x - cx) + sqr(y - cy) - sqr(radius) >= 0, IMPACT)
    
    return automaton


def get_system():
    # Create the composed automaton
    system = CompositeHybridAutomaton("LOVO20_system", [get_automaton()])
    return system


def get_initial_set():
    lotkavolterra = StringVariable("lotkavolterra")
    outside = String("outside")
    x = RealVariable("x")
    y = RealVariable("y")
    cnt = RealVariable("cnt")
    ic = RealPoint([dec(1.3), 1])
    e = dec(0.008)
    initial_set = HybridBoundedConstraintSet({lotkavolterra: outside}, [(ic[0] - e <= x) & (x <= ic[0] + e), y << ic[1], cnt << 0])
    return initial_set


def create_evolver(automaton):
    # Create a GeneralHybridEvolver object
    integrator = TaylorPicardIntegrator(1e-5)
    evolver = GeneralHybridEvolver(automaton)
    
    # Set the evolver configuration
    evolver.set_integrator(integrator)
    evolver.configuration().set_maximum_enclosure_radius(1.0)
    evolver.configuration().set_maximum_step_size(0.09)
    evolver.configuration().set_maximum_spacial_error(1e-5)
    
    return evolver


def get_circle_orbit():
    x = RealVariable("x")
    y = RealVariable("y")
    
    alpha = RealConstant("alpha", 3)
    beta = RealConstant("beta", 3)
    gamma = RealConstant("gamma", 1)
    delta = RealConstant("delta", 1)
    radius = RealConstant("radius", dec(0.15))
    
    cx = gamma / delta
    cy = alpha / beta
    
    circle = HybridAutomaton()
    rotate = DiscreteLocation()
    t = RealVariable("t")
    circle.new_mode(rotate, [let(x) << cx + radius * cos(t), let(y) << cy - radius * sin(t)], [dot(t) << 1])
    simulator = HybridSimulator(circle)
    simulator.configuration().set_step_size(0.1)
    circle_initial = HybridBoundedConstraintSet(rotate, [t << 0])
    circle_time = HybridTerminationCriterion(2 * pi, 1)
    orbit = simulator.orbit(circle_initial, circle_time)
    
    return orbit


def plot_all(LOVO20_orbit, circle_orbit):
    x = RealVariable("x")
    y = RealVariable("y")
    
    print("Plotting evolution flow tube...")
    fig = HybridFigure()
    fig.set_axes(Axes2d(0.6, x, 1.4, 0.6, y, 1.4))
    fig.draw(circle_orbit)
    fig.draw(LOVO20_orbit)
    fig.write("LOVO20")


def verify(orbit):
    has_any_zero_transitions = False
    has_any_two_transitions = False
    
    for enclosure in orbit.final():
        if (not has_any_zero_transitions) and len(enclosure.previous_events()) == 0:
            has_any_zero_transitions = True
        if (not has_any_two_transitions) and len(enclosure.previous_events()) == 2:
            has_any_two_transitions = True
    
    if has_any_zero_transitions:
        print("A final set with zero transitions has been found correctly.")
    else:
        print("No final set with zero transitions has been found!")
    
    if has_any_two_transitions:
        print("A final set with two transitions has been found correctly.")
    else:
        print("No final set with two transitions has been found!")
    
    x = RealVariable("x")
    y = RealVariable("y")
    cnt = RealVariable("cnt")
    
    final_bounds = orbit.final().bounding_box()
    
    print("Trajectory stays in the reference circle for at most", final_bounds[cnt].upper_bound(), "time units: ", end='')
    print("constraint satisfied") if final_bounds[cnt].upper_bound().raw() <= FloatDP(0.2, DoublePrecision()) else print("constraint NOT satisfied!")


if __name__ == '__main__':
    # Get the system
    LOVO20 = get_automaton()
    print(LOVO20)
    
    # Get the initial set
    initial_set = get_initial_set()
    print("initial_set =", initial_set)
    
    # Get the final time
    final_time = HybridTerminationCriterion(dec(3.64), 3)
    
    # Create an evolver object
    evolver = create_evolver(LOVO20)
    print("evolver.configuration() =", evolver.configuration())
    
    # Compute the evolution
    LOVO20_orbit = evolver.orbit(initial_set, final_time, Semantics.UPPER)
    
    # Check number of events
    verify(LOVO20_orbit)
    
    # Get the orbit of the circle to plot, by points
    #  (basically, create an automaton that traces a circle orbit)
    circle_orbit = get_circle_orbit()
    
    # Plot figures
    plot_all(LOVO20_orbit, circle_orbit)
