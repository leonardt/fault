import re
from fault.real_type import Real

try:
    import numpy as np
    from scipy.interpolate import interp1d
    import decida.Data
except ModuleNotFoundError:
    print('Failed to import libraries for results parsing.  Capabilities may be limited.')  # noqa


class SpiceResult:
    def __init__(self, t, v):
        self.t = t
        self.v = v
        self.func = interp1d(t, v, bounds_error=False, fill_value=(v[0], v[-1]))

    def __call__(self, t):
        return self.func(t)
    
# TODO should probably rename this to something like "PWCResult"
class ResultInterp:
    def __init__(self, t, v, interp='linear'):
        self.t = t
        self.v = v
        self.func = interp1d(t, v, bounds_error=False, fill_value=(v[0], v[-1]), kind=interp)

    def __call__(self, t):
        return self.func(t)


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
    data.read_nutmeg(f'{nut_file}')
    return data_to_interp(data=data, time=time)


def psf_parse(psf_file, time='time'):
    data = decida.Data.Data()
    data.read_psf(f'{psf_file}')
    return data_to_interp(data=data, time=time)


def hspice_parse(tr0_file, time='time'):
    data = CSDFData()
    data.read(f'{tr0_file}')
    return data_to_interp(data=data, time=time)


def data_to_interp(data, time, strip_vi=True):
    retval = {}

    # preprocess results as needed
    rdict = {}
    for name in data.names():
        value = data.get(name)
        if strip_vi:
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
        result = SpiceResult(t=time_vec, v=value_vec)

        # add interpolator to dictionary
        retval[name] = result

    # return results
    return retval


def parse_vcd(filename, dut, interp='previous'):
    # unfortunately this vcd parser has an annoyin quirk:
    # it throws away the format specifier for numbers so we can't tell if they're binary or real
    # so "reg [7:0] a = 8'd4;" and "real a = 100.0;" both come back as the string '100'
    # TODO fix this
    filename = 'build/' + filename

    # library doesn't grab timescale, so we do it manually
    with open(filename) as f:
        next = False
        for line in f:
            if next:
                ts = line.strip().split()
                break
            if '$timescale' in line:
                next = True
        else:
            assert False, f'Timescale not found in vcd {filename}'

    scales = {
        'fs': 1e-15,
        'ps': 1e-12,
        'ns': 1e-9,
        'us': 1e-6,
        'ms': 1e-3,
        's': 1e0
    }
    if ts[1] not in scales:
        assert False, f'Unrecognized timescale {ts[1]}'
    timescale = float(ts[0]) * scales[ts[1]]

    from vcdvcd import VCDVCD
    obj = VCDVCD(filename)

    def get_name_from_v(v):
        name_vcd = v['references'][0].split('.')[-1]
        name_fault = re.sub('\[[0-9]*:[0-9]*\]', '', name_vcd)
        return name_fault
    
    def format(name, val_str):
        if not hasattr(dut, name):
            # we don't know what the type is, but we know scipy will try to cast it to float
            # we can't assume bits becasue mlingua etol stuff is in this category
            # we can't assume real becuase bit types with value 'x' come through here too
            try:
                return float(val_str)
            except ValueError:
                return float('nan')
            
        a = getattr(dut, name)
        b = isinstance(type(a), type(Real))
        
        if b:
            return float(val_str)
        else:
            # TODO deal with x and z
            # atm it breaks if the value can't be cast to a float
            if val_str == 'x':
                return float('nan')
            elif val_str == 'z':
                return float('nan')
            return int(val_str, 2)

    data = obj.get_data()
    data = {get_name_from_v(v): v['tv'] for v in data.values()}
    end_time = obj.get_endtime()

    retval = {}
    for port, vs in data.items():
        t, v = zip(*vs)
        t, v = list(t), list(v)
        # append an additional point at the end time
        t.append(end_time)
        v.append(v[-1])
        t, v = [time * timescale for time in t], [format(port, val) for val in v]

        r = ResultInterp(t, v, interp=interp)
        retval[port] = r

    return retval
