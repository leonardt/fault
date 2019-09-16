try:
    import numpy as np
    from scipy.interpolate import interp1d
    import decida.Data
except ModuleNotFoundError:
    print('Failed to import libraries for results parsing.  Capabilities may be limited.')  # noqa


# temporary measure -- CSDF parsing is broken in
# DeCiDa so a simple parser is implemented here
class CSDFData:
    def __init__(self):
        self._names = {'time': 0}
        self._data = None
        self.data = {}

    def names(self):
        return list(self._names.keys())

    def get(self, name):
        return self._data[:, self._names[name]]

    def read(self, file):
        # read in flat data vector
        mode = None
        data = []
        with open(file, 'r') as f:
            for line in f:
                # determine mode
                line = line.strip().split()
                if not line:
                    continue
                elif line[0] == '#N':
                    mode = '#N'
                    line.pop(0)
                elif line[0] == '#C':
                    mode = '#C'
                    line.pop(0)
                    data.append(float(line.pop(0)))
                    line.pop(0)
                elif line[0] == '#;':
                    break
                # parse depending on mode
                if mode == '#N':
                    for tok in line:
                        tok = tok[1:-1]
                        self._names[tok] = len(self._names)
                elif mode == '#C':
                    for tok in line:
                        data.append(float(tok))

        # reshape into numpy array
        nv = len(self._names)
        ns = len(data) // nv
        data = np.array(data, dtype=float)
        data = np.reshape(data, (ns, nv))

        # store using internal numpy array
        self._data = data


def nut_parse(nut_file, time='time'):
    data = decida.Data.Data()
    data.read_nutmeg(nut_file)
    return data_to_interp(data=data, time=time)


def psf_parse(psf_file, time='time'):
    data = decida.Data.Data()
    data.read_psf(psf_file)
    return data_to_interp(data=data, time=time)


def hspice_parse(tr0_file, time='time'):
    data = CSDFData()
    data.read(tr0_file)
    return data_to_interp(data=data, time=time)


def data_to_interp(data, time, strip_vi=True):
    retval = {}

    # preprocess results as needed
    rdict = {}
    for name in data.names():
        value = data.get(name)
        if name.lower().startswith('v(') and name.lower().endswith(')'):
            name = name[2:-1]
        elif name.lower().startswith('i(') and name.lower().endswith(')'):
            name = name[2:-1]
        rdict[name] = value

    # prepare dictionary of interpolators
    time_vec = rdict[time]
    for name, value_vec in rdict.items():
        # skip time variable -- no need to interpolate time to itself
        if name == time:
            continue

        # create interpolator
        result = interp1d(time_vec, value_vec, bounds_error=False,
                          fill_value=(value_vec[0], value_vec[-1]))

        # add interpolator to dictionary
        retval[name] = result

    # return results
    return retval
