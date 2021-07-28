import numpy as np
from fault.result_parse import SpiceResult, ResultInterp


# edge finder is used for measuring phase, freq, etc.
class EdgeNotFoundError(Exception):
    pass


def get_value_domain(results, action, time, get_name):
    style = action.params.pop('style')
    # TODO is this the right way to get the name?
    try:
        res = results[get_name(action.port)]
    except KeyError:
        res = results[get_name(action.port).lower()]

    if not isinstance(res.t, np.ndarray):
        res.t = np.array(res.t)
        res.v = np.array(res.v)

    if isinstance(res, ResultInterp):
        res_style = 'pwc'
    elif isinstance(res, SpiceResult):
        res_style = 'spice'
    else:
        assert False, f'Unrecognized result class {type(res)} for result {res}'
    # TODO default height for spice is different and depends on vsup
    height = action.params.get('height', 0.5)
    if 'height' in action.params:
        action.params.pop('height')
    if style == 'single':
        # equivalent to a regular get_value
        value = res(time)
        if type(value) == np.ndarray:
            value = value.tolist()
        action.value = value
    elif style == 'edge':
        # looking for a nearby rising/falling edge
        # look at find_edge for possible parameters
        value = find_edge(res_style, res.t, res.v, time, height,
                          **action.params)
        action.value = value
    elif style == 'frequency':
        # frequency based on the (previous?) two rising edges
        edges = find_edge(res_style, res.t, res.v, time, height, count=2)
        freq = 1 / (edges[0] - edges[1])
        action.value = freq
    elif style == 'phase':
        # phase of this signal relative to another
        msg = 'Phase read requires reference signal param'
        assert 'ref' in action.params, msg
        res_ref = results[f'{get_name(action.params["ref"])}']
        ref = find_edge(res_style, res_ref.t, res_ref.v, time, height, count=2)
        before_cycle_end = find_edge(res_style, res.t, res.v, time + ref[0],
                                     height)
        fraction = 1 + before_cycle_end[0] / (ref[0] - ref[1])
        # TODO multiply by 2pi?
        action.value = fraction
    elif style == 'block':
        # return a whole chunk of the waveform.
        # returns (t, v) where t is time relative to the get_value action
        assert 'duration' in action.params, 'Block read requires duration'
        duration = action.params['duration']
        # make sure to grab points surrounding requested times so user can
        # interpolate the exact start and end.
        start = max(0, np.argmax(res.t > time) - 1)
        end = ((len(res.t) - 1) if res.t[-1] < time + duration
               else np.argmax(res.t >= time + duration))

        t = res.t[start:end] - time
        v = res.v[start:end]
        action.value = (t, v)
    else:
        raise NotImplementedError(f'Unknown style "{style}"')


def find_edge(res_style, *args, **kwargs):
    if res_style == 'spice':
        return find_edge_spice(*args, **kwargs)
    elif res_style == 'pwc':
        return find_edge_pwc(*args, **kwargs)
    else:
        assert False, f'Unrecognized result style "{res_style}"'


def find_edge_pwc(x, y, t_start, height, forward=False, count=1, rising=True):
    """
    Search through data (x,y) starting at time t_start for when the
    waveform crosses height (defaut is ???). Searches backwards by
    default (frequency now is probably based on the last few edges?)
    """

    # deal with `rising` and `forward`
    # normally a low-to-high finder
    if rising ^ forward:
        y = [(-1 * z + 2 * height) for z in y]
    direction = 1 if forward else -1
    # we want to start on the far side of the interval containing t_start
    # to make sure we catch any edge near t_start
    side = 'left' if forward else 'right'

    start_index = np.searchsorted(x, t_start, side=side)
    if start_index == len(x):
        # happens when forward=False and the edge find is the end of the sim
        start_index -= 1

    i = start_index
    edges = []
    while len(edges) < count:
        # move until we hit low
        while y[i] > height:
            i += direction
            if i < 0 or i >= len(y):
                msg = f'only {len(edges)} of requested {count} edges found'
                raise EdgeNotFoundError(msg)
        # now move until we hit the high
        while y[i] <= height:
            i += direction
            if i < 0 or i >= len(y):
                msg = f'only {len(edges)} of requested {count} edges found'
                raise EdgeNotFoundError(msg)

        # moving forward the crossing happens eactly when we hit the high value
        # moving backward it happens at the last low one we saw (one thing ago)
        t = x[i] if direction == 1 else x[i+1]
        if t == t_start:
            print('EDGE EXACTLY AT EDGE FIND REQUEST')
        elif (t - t_start) * direction < 0:
            # we probably backed up to consider the point half a step before
            # t_start don't count this one, and keep looking
            continue
        edges.append(t - t_start)
    return edges


def find_edge_spice(x, y, t_start, height, forward=False, count=1, rising=True):
    """
    Search through data (x,y) starting at time t_start for when the
    waveform crosses height (defaut is ???). Searches backwards by
    default (frequency now is probably based on the last few edges?)
    """

    # deal with `rising` and `forward`
    # normally a low-to-high finder
    if rising ^ forward:
        y = [(-1 * z + 2 * height) for z in y]
    direction = 1 if forward else -1

    # we want to start on the far side of the interval containing t_start
    # to make sure we catch any edge near t_start
    side = 'right' if forward else 'left'
    bump = -1 if forward else 0
    start_index = np.searchsorted(x, t_start, side=side) + bump
    if start_index == len(x):
        # happens when forward=False and the edge find is the end of the sim
        start_index -= 1

    i = start_index
    edges = []
    while len(edges) < count:
        # move until we hit low
        while y[i] > height:
            i += direction
            if i < 0 or i >= len(y):
                msg = f'only {len(edges)} of requested {count} edges found'
                raise EdgeNotFoundError(msg)
        # now move until we hit the high
        while y[i] <= height:
            i += direction
            if i < 0 or i >= len(y):
                msg = f'only {len(edges)} of requested {count} edges found'
                raise EdgeNotFoundError(msg)

        # the crossing happens from i to i+1
        # fraction is how far you must go from i to (i-direction) to hit the
        # crossing
        fraction = (height - y[i]) / (y[i - direction] - y[i])
        # TODO for a long time this said "x[i + 1] - x[i]", I should
        # triple-check that it's correct now
        t = x[i] + fraction * (x[i-direction] - x[i])
        if t == t_start:
            print('EDGE EXACTLY AT EDGE FIND REQUEST')
        elif (t - t_start) * direction < 0:
            # we probably backed up to consider the point half a step before
            # t_start
            # don't count this one, and keep looking
            continue
        edges.append(t - t_start)
    return edges


def domain_read(cls):
    class DomainGetValue(cls):
        def is_domain_read(self):
            return type(self.params) == dict and 'style' in self.params

        def get_format(self):
            if self.is_domain_read(): 
                # this is a domain read
                # this is pretty hacky...
                return '%0.15f\\n", $realtime/1s);//'
            else:
                return super().get_format()
        
        def update_from_line(self, line):
            if self.is_domain_read():
                # here we temporily put the time in self.value
                # the time will be used as an index into the waveform file,
                # and value will be changed later
                # pycharm complains here that we are defining self.value
                # outside __init__, but we know cls already has self.value
                self.value = float(line.strip())
            else:
                super().update_from_line(line)
            
    return DomainGetValue
