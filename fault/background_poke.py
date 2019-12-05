from fault.actions import Poke
import heapq
import math
from functools import total_ordering
import copy


@total_ordering
class Thread():
    # if sin wave dt is unspecified, use period/default_steps_per_cycle
    default_steps_per_cycle = 10

    # when checking clock value at time t, check time t+epsilon instead
    # this avoids ambiguity when landing exactly on the clock edge
    epsilon = 1e-18

    def __init__(self, time, poke):
        #print('creating thread for', poke, 'at time', time)
        self.poke = copy.copy(poke)
        self.poke.params = None
        self.poke.delay = None
        params = poke.delay
        self.start = time
        self.next_update = time
        type_ = params.get('type', 'clock')

        #print('type_ is', type_)
        #print(params)

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
                    return 1 if cycle_location > (1 - duty_cycle) else 0
                else:
                    return 1 if cycle_location < duty_cycle else 0

            self.get_val = get_val
            self.dt = period/2

        elif type_ == 'sin':
            freq = params.get('freq', 1e6)
            period = params.get('period', 1/freq)
            freq = 1 / period
            amplitude = params.get('amplitude', 1)
            offset = params.get('offset', 0)
            phase_degrees = params.get('phase_degrees', 0)
            conv = math.pi / 180.0
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
        # TODO don't poke at the same time twice
        missed_update_msg = 'Background Poke thread not updated in time'
        assert t <= self.next_update + self.epsilon, missed_update_msg
        if abs(t - self.next_update) < self.epsilon:
            self.next_update = t + self.dt
        value = self.get_val(t)
        poke = copy.copy(self.poke)
        poke.value = value
        return poke

    def __lt__(self, other):
        return self.next_update < other


class ThreadPool():
    # if the next background update is within epsilon of the next manual
    # update, then the background one comes first
    # Which comes first is arbitrary, but this epsilon makes it consistent
    epsilon = 1e-18

    def __init__(self, time):
        self.t = time
        self.background_threads = []
        self.active_ports = set()

    def get_next_update_time(self):
        if len(self.background_threads) == 0:
            return float('inf')
        else:
            return self.background_threads[0].next_update

    def delay(self, t_delay):
        '''
        Create a list of actions that need to happen during this delay.
        Returns (free_time, actions), where free_time is the delay that should
        happen before the first action in actions.
        '''
        #print('Thread pool is doing a delay of ', t_delay, 'at time', self.t)
        t = self.t
        t_end = self.t + t_delay
        free_time = self.get_next_update_time() - self.t
        if free_time > t_delay:
            #print('pool update not needed', t)
            self.t = t_end
            return (t_delay, [])
        else:
            actions = []
            #print('entering while loop')
            while self.get_next_update_time() <= t_end + self.epsilon:
                thread = heapq.heappop(self.background_threads)
                action = thread.step(t)
                heapq.heappush(self.background_threads, thread)

                # we had to put the thread back on the heap in order to
                # calculate the next update
                next_thing_time = min(self.get_next_update_time(), t_end)
                #print('calculated next thing time', next_thing_time, 'at time', t)
                action.delay = next_thing_time - t
                t = next_thing_time
                actions.append(action)

            # t_end has less floating point error than t
            self.t = t_end
            #print('ending updates at time', t_end)
            return (free_time, actions)

    def add(self, background_poke):
        error_msg = 'Cannot add existing background thread'
        assert background_poke.port not in self.active_ports, error_msg
        self.active_ports.add(background_poke.port)
        thread = Thread(self.t, background_poke)
        heapq.heappush(self.background_threads, thread)

    def remove(self, port):
        self.active_ports.remove(port)
        for thread in self.background_threads:
            if thread.poke.port == port:
                offender = thread
        self.background_threads.remove(offender)
        poke = offender.step(self.t)
        if poke is None:
            return []
        else:
            return [poke]

    def process(self, action, delay):
        new_action_list = []
        is_background = (isinstance(action, Poke)
                         and type(action.delay) == dict)

        # check whether this is a poke taking over a background port
        if (isinstance(action, Poke)
            and action.port in self.active_ports):
            new_action_list += self.remove(action.port)

        # if the new port is background we must add it before doing delay
        if is_background:
            self.add(action)

        # we might cut action's delay short to allow some background pokes
        new_delay, actions = self.delay(delay)

        # now we add this (shortened) action back in
        if not is_background:
            # TODO: we used to use copies of the action so we weren't editing
            # the delay of an action owned by someone else. But with the new
            # Read action it's important that the object doesn't change 
            # because the user is holding a pointer to the old Read object
            action.delay = new_delay
            new_action_list.append(action)
            #new_action = copy.copy(action)
            #new_action.delay = new_delay
            #new_action_list.append(new_action)

        new_action_list += actions
        #print('ended up with', len(new_action_list), 'new actions')
        #print('delay of first', new_action_list[0].delay, 'last', new_action_list[-1].delay)
        #if len(new_action_list) > 1:
        #    for action in new_action_list:
        #        print('\t', action, '\t', action.delay)
        return new_action_list


def process_action_list(actions, clock_step_delay):
    """
    Replace Pokes with background_params with many individual pokes.
    Automatically interleaves multiple background tasks with other pokes.
    Throws a NotImplementedError if there's a background task during an
    interval of time not known at compile time.
    """

    def get_delay(a):
        if not hasattr(a, 'delay'):
            return getattr(a, 'time', 0)
        elif a.delay is not None:
            if type(a.delay) == dict:
                return 0
            else:
                return a.delay
        else:
            return clock_step_delay

    background_pool = ThreadPool(0)
    new_action_list = []
    for a in actions:
        delay = get_delay(a)
        new_action_list += background_pool.process(a, delay)
    return new_action_list
