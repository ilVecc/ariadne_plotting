@DeprecationWarning
def menu_choose_variables(var_names, all_variables):
    def safe_get(var_name):
        var = None
        while var is None:
            var = input(f'choice: {var_name} <- ')
            try:
                var = [str(v) for v in all_variables].index(var)
                break
            except ValueError:
                try:
                    var = int(var) - 1
                    if var in range(len(all_variables)):
                        break
                    print('### value out of range')
                    var = None
                except ValueError:
                    print('### value must be <index> or <variable name>')
        return all_variables[var]
    
    print('Choose the variables to plot: ')
    for i, v in enumerate(all_variables):
        print(f'\t{i + 1}. {v}')
    return tuple(safe_get(var) for var in var_names)
