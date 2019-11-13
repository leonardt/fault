from fault.actions import Poke
import heapq, math
from functools import total_ordering


@total_ordering
class Thread():
    # if sin wave dt is unspecified, use period/default_steps_per_cycle
    default_steps_per_cycle = 20

    # when checking clock value at time t, check time t+epsilon instead
    # this avoids ambiguity when landing exactly on the clock edge
    epsilon = 1e-18


    def __init__(self, time, poke):
        self.poke = poke.copy()
        self.poke.params = None
        self.poke.delay = None
        params = poke.params
        self.start = time
        self.next_update = 0
        type_ = params.get('type', 'clock')

        # Each type must set a get_val(t) function and a dt
        if type_ == 'clock':
            freq = params.get('freq', 1e6)
            period = params.get('period', 1/freq)
            freq = 1 / period
            duty_cycle = params.get('duty_cycle', 0.5)
            initial_value = params.get('initial_value', 0)

            def get_val(t):
                cycle_location = ((t - self.start + self.epsilon) / period) % 1
                if initial_value == 0:
                    return cycle_location > (1 - duty_cycle)
                else:
                    return cycle_location < duty_cycle

            self.get_val = get_val
            self.dt = period/2

        elif type_ == 'sin':
            freq = params.get('freq', 1e6)
            period = params.get('period', 1/freq)
            freq = 1 / period
            amplitude = params.get('amplitude', 1)
            offset = params.get('offset', 0)
            phase_degrees = params.get('phase_degrees', 0)
            conv = math.pi / 180
            phase_radians = params.get('phase_radians', phase_degrees * conv)

            def get_val(t):
                x = math.sin((t-self.start)*freq*2*math.pi + phase_radians)
                return amplitude * x + offset

            self.get_val = get_val
            self.dt = params.get('dt', 1 / (freq*self.default_steps_per_cycle))

    def step(self, t):
        '''
        Returns a new Poke object with the correct value set for time t.
        Sets the port and value but NOT the delay.
        '''
        missed_update_msg = 'Background Poke thread not updated in time'
        assert t <= self.next_update + self.epsilon, missed_update_msg
        value = self.get_val(t)
        poke = self.poke.copy()
        poke.value = value
        return poke


    def __lt__(self, other):
        return self.next_update < other

class ThreadPool():
    pass


def process_action_list(actions, clock_step_delay):
    """
    Replace Pokes with background_params with many individual pokes.
    Automatically interleaves multiple background tasks with other pokes.
    Throws a NotImplementedError if there's a background task during an 
    interval of time not known at compile time.
    """

    new_action_list = []
    t = 0
    for a in actions:
        if isinstance(a, Poke) and a.background_params is not None:
            #do something
            pass
        else:
            new_action_list.append(a)


