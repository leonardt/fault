from fault.actions import Poke, Var
import heapq
import math
from functools import total_ordering
import copy
from fault.target import Target
from fault.actions import Delay


@total_ordering
class Thread():
    # if sin wave dt is unspecified, use period/default_steps_per_cycle
    default_steps_per_cycle = 10

    # when checking clock value at time t, check time t+epsilon instead
    # this avoids ambiguity when landing exactly on the clock edge
    # Also, used to check whether a step was supposed to have happened exactly
    # on a scheduled update, or is too early and we should reschedule
    epsilon = 1e-17

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

        elif type_ == 'ramp':
            start = params.get('start', 0)
            stop = params.get('stop', None)
            rate = params.get('rate', 1) # volts per second
            etol = params.get('etol', 0.1)
            assert etol > 0, 'Ramp error tolerance must be positive'
            dt = abs(etol / rate)

            def get_val(t):
                x = start + rate * (t - self.start)
                if stop != None:
                    if (rate>0 and x>stop) or (rate<0 and x<stop):
                        x = stop
                        self.dt = float('inf')
                return x
            self.get_val = get_val
            self.dt = dt

        elif type_ == 'future':
            wait = params.get('wait', None)
            waits = params.get('waits', [wait])
            value = params.get('value', poke.value)
            values = params.get('values', [value])

            # for the duration of wait[i], output shoud be value[i]
            values = [None] + values
            waits = waits + [float('inf')]

            self.future_count = 0
            def get_val(t):
                if t + 2*self.epsilon > self.future_next:
                    assert t - self.future_next < self.epsilon, 'Missed update in future background poke'
                    self.future_count += 1
                    self.future_next += waits[self.future_count]
                    self.dt = self.future_next - t
                v = values[self.future_count]
                if abs(t-self.next_update) <= self.epsilon:
                    if self.future_next - (self.next_update + self.dt) < -self.epsilon:
                        pass
                else:
                    if self.future_next - self.next_update < -self.epsilon:
                        pass
                #assert self.next_update+self.dt <= self.future_next
                return v
            self.get_val = get_val
            self.dt = waits[0]
            self.future_next = self.start + self.dt
        else:
            assert False, 'Unrecognized background_poke type '+str(type_)



    def step(self, t):
        '''
        Returns a new Poke object with the correct value set for time t.
        Sets the port and value but NOT the delay.
        '''
        # TODO don't poke at the same time twice
        missed_update_msg = 'Background Poke thread not updated in time'
        assert t <= self.next_update + self.epsilon, missed_update_msg

        # must call get_val before calculating next_update because it can alter self.dt
        value = self.get_val(t)
        if abs(t - self.next_update) < 2*self.epsilon:
            self.next_update = t + self.dt

        if value is None:
            # The actual delay will get set later
            return Delay(-1)
        else:
            poke = copy.copy(self.poke)
            poke.value = value
            return poke

    def __lt__(self, other):
        return self.next_update < other


class ThreadPool():
    # if the next background update is within epsilon of the next manual
    # update, then the background one comes first
    # Which comes first is arbitrary, but this epsilon makes it consistent
    epsilon = 1e-17 # 1e-18

    def __init__(self, time):
        self.t = time
        self.background_threads = []
        self.active_ports = set()

    def set_action_delay(self, action, delay):
        if isinstance(action, Delay):
            action.time = delay
        else:
            action.delay = delay

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
        # note that free_time here is actually the free time until the next pool update,
        # the actual time returned is until the next action and might be less than free_time
        free_time = self.get_next_update_time() - self.t
        if free_time > t_delay:
            self.t = t_end
            return (t_delay, [])
        else:
            actions = []
            t += free_time;
            #print('entering while loop')
            while self.get_next_update_time() <= t_end + self.epsilon:
                thread = heapq.heappop(self.background_threads)
                action = thread.step(t)
                heapq.heappush(self.background_threads, thread)

                # we had to put the thread back on the heap in order to
                # calculate the next update
                next_thing_time = min(self.get_next_update_time(), t_end)
                #print('\ncalculated next thing time', next_thing_time, 'at time', t)
                delay = next_thing_time - t
                self.set_action_delay(action, delay)
                #print('also adding action', action, 'delay', action.delay)
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
            if thread.poke.port is port:
                offender = thread
        self.background_threads.remove(offender)
        heapq.heapify(self.background_threads)
        poke = offender.step(self.t)
        if poke is None:
            # TODO I don't think this path is ever taken?
            return []
        else:
            self.set_action_delay(poke, 0)
            return [poke]

    def process(self, action, delay):
        new_action_list = []
        is_background = (isinstance(action, Poke)
                         and type(action.delay) == dict)

        # check whether this is a poke taking over a background port
        # TODO if the port is a Var, just hope it's not taking over
        if (isinstance(action, Poke)
            and not isinstance(action.port, Var)
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
            self.set_action_delay(action, new_delay)
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
            return 0 # clock_step_delay

    background_pool = ThreadPool(0)
    new_action_list = []
    for a in actions:
        delay = get_delay(a)
        new_action_list += background_pool.process(a, delay)
    return new_action_list

def background_poke_target(cls):
    class BackgroundPokeTarget(cls):
        def run(self, *args, **kwargs):
            assert (len(args) > 0 and isinstance(args[0], list),
                    'Expected first arg to "target.run" to be an action list')
            actions = args[0]
            new_actions = process_action_list(actions, self.clock_step_delay)
            new_args = (new_actions, *args[1:])
            super().run(*new_args, **kwargs)
    return BackgroundPokeTarget
