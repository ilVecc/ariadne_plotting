#!/usr/bin/python3

from pyariadne import *


def get_tank():
    # Declare the system constants
    alpha = RealConstant("alpha", dec(0.02))
    beta = RealConstant("beta", dec(0.3))
    
    # Declare the variables for the dynamics
    aperture = RealVariable("aperture")
    height = RealVariable("height")
    
    # Create the tank automaton
    automaton = HybridAutomaton()
    
    # The water level is always given by the same dynamic.
    # The inflow is controlled by the valve aperture, the outflow depends on the
    # pressure, which is proportional to the water height.
    automaton.new_mode([dot(height) << beta * aperture - alpha * height])
    
    return automaton


def get_valve():
    # Declare some constants. Note that system parameters should be given as variables.
    T = RealConstant("T", 4)
    
    # Declare the shared system variables
    aperture = RealVariable("aperture")
    
    # Declare the events we use
    stop_opening = DiscreteEvent("stop_opening")
    stop_closing = DiscreteEvent("stop_closing")
    can_open = DiscreteEvent("can_open")
    can_close = DiscreteEvent("can_close")
    
    # Declare the variable for the automaton name
    valve = StringVariable("valve")
    
    # Create the valve automaton
    automaton = HybridAutomaton(valve.name())
    
    # Declare the values the valve variable can have
    opening = DiscreteLocation({valve: "opening"})
    closed = DiscreteLocation({valve: "closed"})
    opened = DiscreteLocation({valve: "opened"})
    closing = DiscreteLocation({valve: "closing"})
    
    # Define the algebraic equations for the opened/closed locations.
    automaton.new_mode(opened, [let(aperture) << 1])
    automaton.new_mode(closed, [let(aperture) << 0])
    # Define the differential equations for the opening/closing locations.
    automaton.new_mode(opening, [dot(aperture) << +1 / T])
    automaton.new_mode(closing, [dot(aperture) << -1 / T])
    
    # Define the transitions: source location, event and target location
    # then a mix of reset, guard and event kind can be present; if the event kind
    # is not specified, then also the guard can't be specified: this implicitly
    # means that the event is an input event for this automaton.
    automaton.new_transition(closed, can_open, opening, [next(aperture) << aperture])
    automaton.new_transition(opening, stop_opening, opened, aperture >= 1, URGENT)
    automaton.new_transition(opened, can_close, closing, [next(aperture) << aperture])
    automaton.new_transition(closing, stop_closing, closed, aperture <= 0, URGENT)
    automaton.new_transition(opening, can_close, closing, [next(aperture) << aperture])
    automaton.new_transition(closing, can_open, opening, [next(aperture) << aperture])
    
    return automaton


def get_controller():
    # Declare some constants
    hmin = RealConstant("hmin", dec(5.75))
    hmax = RealConstant("hmax", dec(7.75))
    delta = RealConstant("delta", dec(0.02))
    
    # Declare the shared system variables
    height = RealVariable("height")
    
    # Declare the events we use
    can_open = DiscreteEvent("can_open")
    can_close = DiscreteEvent("can_close")
    must_open = DiscreteEvent("must_open")
    must_close = DiscreteEvent("must_close")
    
    # Declare the variable for the automaton name
    controller = StringVariable("controller")
    
    # Create the controller automaton
    automaton = HybridAutomaton(controller.name())
    
    # Declare the locations for the controller
    rising = DiscreteLocation({controller: "rising"})
    falling = DiscreteLocation({controller: "falling"})
    
    # Instantiate modes for each location with no dynamics
    automaton.new_mode(rising)
    automaton.new_mode(falling)
    
    # Specify the invariants valid in each mode. Note that every invariant
    # must have an action label. This is used internally, for example, to
    # check non-blockingness of urgent actions.
    automaton.new_invariant(falling, height >= hmin - delta, must_open)
    automaton.new_invariant(rising, height <= hmax + delta, must_close)
    
    # Specify the transitions, starting from the source location, according to an event, to a target location
    # Following those arguments you specify a guard and whether the event is permissive or urgent.
    automaton.new_transition(falling, can_open, rising, height <= hmin + delta, PERMISSIVE)
    automaton.new_transition(rising, can_close, falling, height >= hmax - delta, PERMISSIVE)
    
    return automaton


def get_system():
    # Create the composed automaton
    system = CompositeHybridAutomaton("watertank", [get_tank(), get_valve(), get_controller()])
    
    # Print the system description on the command line
    print("system =", system)
    
    return system


def get_initial_set():
    # Re-introduce variables to be used for the initial set
    height = RealVariable("height")
    valve = StringVariable("valve")
    controller = StringVariable("controller")
    opened = String("opened")
    rising = String("rising")
    
    # Define the initial set, by supplying the location as a list of locations for each composed automata, and
    # the continuous set as a list of variable assignments for each variable controlled on that location
    # (the assignment can be either a singleton value using the == symbol or an interval using the <= symbols)
    initial_set = HybridBoundedConstraintSet({valve: opened, controller: rising}, [(dec(6.9) <= height) & (height <= 7)])
    
    # Print the initial set on the command line
    print("initial_set =", initial_set)
    
    return initial_set


def get_final_time():
    # Define the final time: continuous time and maximum number of transitions
    final_time = HybridTime(dec(30.0), 5)
    print("final_time =", final_time)
    
    return final_time


def simulate_evolution(system, initial_set, final_time):
    # Re-introduce the shared system variables required for the initial set
    aperture = RealVariable("aperture")
    height = RealVariable("height")
    
    # Create a simulator object
    simulator = HybridSimulator(system)
    simulator.configuration().set_step_size(0.01)
    
    print("simulator.configuration() = ", simulator.configuration())
    
    # Compute a simulation trajectory
    print("Computing simulation trajectory...")
    orbit = simulator.orbit(initial_set, HybridTerminationCriterion(final_time))
    
    # Plot the simulation trajectory using all different projections
    print("Plotting simulation trajectory..")
    plot("plots/simulation/simulation_t-height", Axes2d(0, TimeVariable(), 30, 5, height, 9), orbit)
    plot("plots/simulation/simulation_t-aperture", Axes2d(0, TimeVariable(), 30, -0.1, aperture, 1.1), orbit)
    plot("plots/simulation/simulation_height-aperture", Axes2d(5, height, 9, -0.1, aperture, 1.1), orbit)
    print("Done computing and plotting simulation trajectory..")


def create_evolver(system):
    # Create a GeneralHybridEvolver object
    evolver = GeneralHybridEvolver(system)
    
    # Set the evolver configuration
    evolver.configuration().set_maximum_enclosure_radius(3.0)
    evolver.configuration().set_maximum_step_size(0.25)
    
    print("evolver.configuration() =", evolver.configuration())
    
    return evolver


def compute_evolution(evolver, initial_set, final_time):
    # Re-introduce the shared system variables required for plotting
    aperture = RealVariable("aperture")
    height = RealVariable("height")
    time = TimeVariable()
    
    # Compute the evolution flow tube using upper semantics
    print("Computing evolution flow tube...")
    orbit = evolver.orbit(initial_set, HybridTerminationCriterion(final_time), Semantics.UPPER)
    # with open("log.txt", "w") as f:
    #     print(orbit, file=f)
    r = orbit.reach()  # type: HybridEnclosureListSet
    return r
    
    # orbit.initial() : the initial set of the orbit.
    # orbit.reach()   : the set of points reached by evolution from the given initial set over the evolution time.
    # orbit.final()   : the set of points reached by evolution from the given initial set at the final evolution time.
    
    # # Plot the flow tube using two different projections
    # print("Plotting evolution flow tube...")
    # plot("plots/finite/finite_evolution_t-height", Axes2d(0, time, 30, 5, height, 9), orbit)
    # plot("plots/finite/finite_evolution_t-aperture", Axes2d(0, time, 30, -0.1, aperture, 1.1), orbit)
    # plot("plots/finite/finite_evolution_height-aperture", Axes2d(5, height, 9, -0.1, aperture, 1.1), orbit)
    # print("Done computing and plotting evolution flow tube!\n")


def create_analyser(evolver):
    # Create a ReachabilityAnalyser object
    analyser = HybridReachabilityAnalyser(evolver)
    
    #  Set the analyser configuration
    analyser.configuration().set_maximum_grid_fineness(6)
    analyser.configuration().set_lock_to_grid_time(5)
    
    print("analyser.configuration() =", analyser.configuration())
    
    return analyser


def compute_reachability(analyser, initial_set, final_time):
    # Re-introduce the shared system variables required for plotting
    aperture = RealVariable("aperture")
    height = RealVariable("height")
    
    # Compute over-approximation to finite-time reachable set using upper semantics.
    print("Computing upper reach set...")
    upper_reach = analyser.upper_reach(initial_set, final_time)
    print("Plotting upper reach set...")
    plot("plots/reach/upper_reach", Axes2d(5, height, 9, -0.1, aperture, 1.1), upper_reach)
    print("Done computing and plotting upper reach set!\n")
    
    # Compute over-approximation to infinite-time reachable set using upper semantics.
    print("Computing outer chain reach set...")
    outer_chain_reach = analyser.outer_chain_reach(initial_set)
    print("Plotting outer chain reach set...")
    plot("plots/reach/outer_chain_reach", Axes2d(5, height, 9, -0.1, aperture, 1.1), outer_chain_reach)
    print("Done computing and plotting outer chain reach set!\n")


if __name__ == '__main__':
    # Get the system, the initial set and the final time
    system = get_system()
    initial_set = get_initial_set()
    final_time = get_final_time()
    
    # evoluzione classica a tempo continuo [puntuale] (integratore con metodo Runge-Kutta)
    
    # # Compute an approximate simulation of the system evolution
    # simulate_evolution(system, initial_set, final_time)
    
    # evoluzione classica a tempo continuo con incertezza [insiemistico; in pratica abbiamo più traiettorie (per questo le aree arancioni nel plot)]
    
    # Create an evolver object and Compute the system evolution
    evolver = create_evolver(system)
    r = compute_evolution(evolver, initial_set, final_time)

    import matplotlib.pyplot as plt
    # time - aperture
    for encl in r:
        points = encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(2, 0)
        x = [p.x for p in points]
        y = [p.y for p in points]
        plt.plot(x, y)
    plt.show()
    # time - height
    for encl in r:
        points = encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(2, 1)
        x = [p.x for p in points]
        y = [p.y for p in points]
        plt.plot(x, y)
    plt.show()
    # aperture - height
    for encl in r:
        points = encl.continuous_set().state_time_auxiliary_set().affine_over_approximation().boundary(0, 1)
        x = [p.x for p in points]
        y = [p.y for p in points]
        plt.plot(x, y)
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
    
    # come per l'evolver, ma si discretizza periodicamente sulla griglia dei possibili stati, così possiamo scalare facilmente (qui abbiamo i rettangoli)
    # non credo di aver capito bene il perché, ma il tempo non è più disponibile a causa dell'utilizzo della griglia (quindi ci fermiamo alla 5a location)
    # qui abbiamo anche "outer chain reach", che è evoluzione a tempo infinito (ottenibile evitando divergenza numerica causa approssimazioni e reachable set
    # illimitato tramite l'impostazione di un bounding domain)
    
    # # Create an analyser object and Compute the system reachability
    # analyser = create_analyser(evolver)
    # compute_reachability(analyser, initial_set, final_time)


def yaml_test():
    # # Create the composed automaton
    # watertank_system = get_system()
    watertank_system = get_valve()
    
    # Print the system description on the command line
    print("System: ", watertank_system)
    
    # controller = StringVariable("controller")
    # rising = DiscreteLocation({controller: "rising"})
    
    # import pickle
    # s = pickle.dumps(can_open)
    # print(s)
    # unpick = pickle.loads(s)
    # print(unpick)
    
    import yaml
    
    def DiscreteLocation_representer(dumper, data):
        return dumper.represent_scalar(u'!DiscreteLocation', u'%s' % data)
    
    def DiscreteLocation_constructor(loader, node):
        value = loader.construct_scalar(node)
        variable, state = value[1:-1].split("|")
        return DiscreteLocation({StringVariable(variable): state})
    
    yaml.add_representer(DiscreteLocation, DiscreteLocation_representer)
    yaml.add_constructor("!DiscreteLocation", DiscreteLocation_constructor)
    
    yamlData = yaml.dump(watertank_system)
    print(yamlData)
    
    yaml_rising = yaml.load(yamlData, Loader=yaml.FullLoader)
    print(yaml_rising)
