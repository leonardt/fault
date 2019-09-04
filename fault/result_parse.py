try:
    import numpy as np
    from scipy.interpolate import interp1d
    from decida.Data import Data
except ModuleNotFoundError:
    print('Failed to import libraries for results parsing.  Capabilities may be limited.')  # noqa


def nut_parse(file):
    d = Data()
    d.read_nutmeg(file)
    return dict_to_interp({name: d.get(name) for name in d.names()})


def hspice_parse(file):
    d = Data()
    d.read_hspice(file)
    return dict_to_interp({name: d.get(name) for name in d.names()})


def dict_to_interp(dict):
    retval = {}

    time_vec = dict['time']
    for name, value_vec in dict.items():
        # skip time variable -- no need to interpolate time to itself
        if name == 'time':
            continue

        # create interpolator
        result = interp1d(time_vec, value_vec, bounds_error=False,
                          fill_value=(value_vec[0], value_vec[-1]))

        # add interpolator to dictionary
        retval[name] = result

    # return results
    return retval
