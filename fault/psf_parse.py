import re
try:
    import numpy as np
    from scipy.interpolate import interp1d
except ModuleNotFoundError:
    print('Failed to load libraries for psf_parse.')


def psf_parse(file_):
    # parse the file
    section = None
    read_mode = None
    variables = []
    values = []
    with open(file_, 'r') as f:
        for line in f:
            # split line into tokens and strip quotes
            tokens = line.strip().split()
            tokens = [token.strip('"') for token in tokens]
            if len(tokens) == 0:
                continue

            # change section mode if needed
            if tokens[0] == 'TRACE':
                section = 'TRACE'
                continue
            elif tokens[0] == 'VALUE':
                section = 'VALUE'
                continue

            # parse data in a section-dependent manner
            if section == 'TRACE':
                if tokens[0] == 'group':
                    continue
                else:
                    variables.append(tokens[0])
            elif section == 'VALUE':
                for token in tokens:
                    if token == 'END':
                        break
                    elif token == 'TIME':
                        read_mode = 'TIME'
                    elif token == 'group':
                        read_mode = 'group'
                    elif read_mode == 'TIME':
                        values.append((float(token), []))
                        read_mode = None
                    elif read_mode == 'group':
                        values[-1][1].append(float(token))
                    else:
                        raise Exception('Unknown token parsing state.')

    # get vector of time values
    time_vec = np.array([value[0] for value in values])

    # re-name voltage variables for consistency
    renamed = []
    for variable in variables:
        m = re.match(r'[vV]\((.+)\)', variable)
        if m:
            renamed.append(m.groups(0)[0])
        else:
            renamed.append(variable)

    # return a dictionary of time-to-value interpolators
    results = {}
    for k, variable in enumerate(renamed):
        # create vector values for this variable
        value_vec = np.array([value[1][k] for value in values])

        # create interpolator
        result = interp1d(time_vec, value_vec, bounds_error=False,
                          fill_value=(value_vec[0], value_vec[-1]))

        # add interpolator to dictionary
        results[variable] = result

    # return results
    return results
