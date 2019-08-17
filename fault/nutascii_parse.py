try:
    import numpy as np
    from scipy.interpolate import interp1d
except ModuleNotFoundError:
    print('Failed to load libraries for nutascii_parse.')


def nutascii_parse(file_):
    # parse the file
    section = None
    variables = []
    values = []
    with open(file_, 'r') as f:
        for line in f:
            # split line into tokens
            tokens = line.strip().split()
            if len(tokens) == 0:
                continue

            # change section mode if needed
            if tokens[0] == 'Values:':
                section = 'Values'
                tokens = tokens[1:]
            elif tokens[0] == 'Variables:':
                section = 'Variables'
                tokens = tokens[1:]

            # parse data in a section-dependent manner
            if section == 'Variables' and len(tokens) >= 2:
                # sanity check
                assert int(tokens[0]) == len(variables), 'Out of sync while parsing variables.'  # noqa
                # add variable
                variables.append(tokens[1])
            elif section == 'Values':
                # start a new list if needed
                for token in tokens:
                    # special handling for first entry
                    if not values or len(values[-1]) == len(variables):
                        # sanity check
                        assert int(token) == len(values), 'Out of sync while parsing values.'  # noqa
                        # clear the value_start flag and start a new
                        # list of values
                        values.append([])
                        continue
                    else:
                        values[-1].append(float(token))
    # sanity check
    if len(values) > 0:
        assert len(values[-1]) == len(variables), 'Missing values at end of file.'  # noqa

    # get vector of time values
    time_vec = np.array([value[variables.index('time')]
                         for value in values])

    # return a dictionary of time-to-value interpolators
    results = {}
    for k, variable in enumerate(variables):
        # skip time variable -- no need to interpolate time to itself
        if variable == 'time':
            continue

        # create vector values for this variable
        value_vec = np.array([value[k] for value in values])

        # create interpolator
        result = interp1d(time_vec, value_vec, bounds_error=False,
                          fill_value=(value_vec[0], value_vec[-1]))

        # add interpolator to dictionary
        results[variable] = result

    # return results
    return results
