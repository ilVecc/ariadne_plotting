from backend import plotting_backend
from backend.plotting_backend import get_all_variables
from systems import tutorial_system

if __name__ == '__main__':
    # build a system as usual
    system = tutorial_system.get_system()
    initial_set = tutorial_system.get_initial_set()
    final_time = tutorial_system.get_final_time()
    # evolve it and extract the orbit
    evolver = tutorial_system.create_evolver(system)
    orbit = tutorial_system.compute_evolution(evolver, initial_set, final_time)
    
    # transform the reach to a dataframe and then plot it
    var_list = get_all_variables(system)  # or simply ['t', 'height']
    var_list = ['t', 'height']
    df = plotting_backend.orbit_to_dataframe(orbit_reach=orbit.reach(), var_list=var_list, collapse=False)
    fig = plotting_backend.plot_trajectory(df, *var_list)
    fig.show()
