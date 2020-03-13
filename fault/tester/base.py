import logging
import magma as m
from abc import abstractmethod
from ..wrapper import CircuitWrapper, PortWrapper
from ..select_path import SelectPath
from ..wrapped_internal_port import WrappedVerilogInternalPort
from ..magma_utils import is_recursive_type
import inspect
from hwtypes import BitVector


class TesterBase:
    def __init__(self, circuit: m.Circuit, clock: m.Clock = None,
                 reset: m.Reset = None, poke_delay_default=None,
                 expect_strict_default=True):
        """
        `circuit`: the device under test (a magma circuit)
        `clock`: optional, a port from `circuit` corresponding to the clock
        `reset`: optional, a port from `circuit` corresponding to the reset
        `expect_strict_default`: if True, use strict equality check if
        not specified by the user.
        """
        if hasattr(circuit, "circuit_definition"):
            circuit = circuit.circuit_definition
        self._circuit = circuit
        self.poke_delay_default = poke_delay_default
        self.expect_strict_default = expect_strict_default
        self.actions = []
        if clock is not None and not isinstance(clock, m.Clock):
            raise TypeError(f"Expected clock port: {clock, type(clock)}")
        self.clock = clock
        # Make sure the user has initialized the clock before stepping it
        # While verilator initializes the clock value to 0, this assumption
        # does not hold for system verilog, so we log a warning (as to not
        # break existing TBs)
        self.clock_initialized = False
        # Only report once, in case the user calls step with an uninitialized
        # clock many times
        self.clock_init_warning_reported = False
        if reset is not None and not isinstance(reset, m.Reset):
            raise TypeError(f"Expected reset port: {reset, type(reset)}")
        self.reset_port = reset

    @abstractmethod
    def _poke(self, port, value, delay=None):
        raise NotImplementedError()

    def poke(self, port, value, delay=None):
        """
        Set `port` to be `value`
        """
        # set defaults
        if delay is None:
            delay = self.poke_delay_default

        if port is self.clock:
            self.clock_initialized = True

        def recurse(port):
            if isinstance(value, dict):
                for k, v in value.items():
                    self.poke(getattr(port, k), v)
            elif isinstance(port, m.Array) and \
                    not issubclass(type(port).T, m.Digital) and \
                    isinstance(value, (int, BitVector, tuple, dict)):
                # Broadcast value to children
                for p in port:
                    self.poke(p, value, delay)
            else:
                _value = value
                if isinstance(_value, int):
                    _value = BitVector[len(port)](_value)
                for p, v in zip(port, _value):
                    self.poke(p, v, delay)

        if isinstance(port, PortWrapper):
            port = port.select_path
        # implement poke
        if isinstance(port, SelectPath):
            if (is_recursive_type(type(port[-1]))
                or (not isinstance(port[-1], WrappedVerilogInternalPort) and
                    isinstance(port[-1].name, m.ref.AnonRef))):
                return recurse(port[-1])
        elif is_recursive_type(type(port)):
            return recurse(port)
        elif not isinstance(port, WrappedVerilogInternalPort) and\
                isinstance(port.name, m.ref.AnonRef):
            return recurse(port)

        self._poke(port, value, delay)

    @abstractmethod
    def peek(self, port):
        """
        Returns a handle to the current value of `port`
        """
        raise NotImplementedError()

    @abstractmethod
    def print(self, format_str, *args):
        """
        Prints out `format_str`

        `*args` should be a variable number of magma ports used to fill in the
        format string
        """
        raise NotImplementedError()

    @abstractmethod
    def assert_(self, expr):
        """
        Asserts `expr` is true
        """
        raise NotImplementedError()

    @abstractmethod
    def _expect(self, port, value, strict=None, caller=None, **kwargs):
        raise NotImplementedError()

    def expect(self, port, value, strict=None, caller=None, **kwargs):
        """
        Expect the current value of `port` to be `value`
        """
        # set defaults
        if strict is None:
            strict = self.expect_strict_default
        if caller is None:
            try:
                caller = inspect.getframeinfo(inspect.stack()[1][0])
            except IndexError:
                pass

        def recurse(port):
            if isinstance(value, dict):
                for k, v in value.items():
                    self.expect(port=getattr(port, k), value=v, strict=strict,
                                caller=caller, **kwargs)
            elif isinstance(port, m.Array) and \
                    not issubclass(type(port).T, m.Digital) and \
                    isinstance(value, (int, BitVector, tuple, dict)):
                # Broadcast value to children
                for p in port:
                    self.expect(port=p, value=value, strict=strict,
                                caller=caller, **kwargs)
            else:
                _value = value
                if isinstance(_value, int):
                    _value = BitVector[len(port)](_value)
                for p, v in zip(port, _value):
                    self.expect(port=p, value=v, strict=strict, caller=caller,
                                **kwargs)

        if isinstance(port, PortWrapper):
            port = port.select_path
        if isinstance(port, SelectPath):
            if (is_recursive_type(type(port[-1]))
                or (not isinstance(port[-1], WrappedVerilogInternalPort)
                    and isinstance(port[-1].name, m.ref.AnonRef))):
                return recurse(port[-1])
        elif is_recursive_type(type(port)):
            return recurse(port)
        elif not isinstance(port, WrappedVerilogInternalPort) and \
                isinstance(port.name, m.ref.AnonRef):
            return recurse(port)
        self._expect(port, value, strict, caller, **kwargs)

    @abstractmethod
    def eval(self):
        """
        Evaluate the DUT given the current input port values
        """
        raise NotImplementedError()

    @abstractmethod
    def delay(self, time):
        """
        Wait the specified amount of time before proceeding
        """
        raise NotImplementedError()

    @abstractmethod
    def get_value(self, port):
        """
        Returns an object with a "value" property that will
        be filled after the simulation completes.
        """
        raise NotImplementedError()

    @abstractmethod
    def step(self, steps=1):
        """
        Step the clock `steps` times.
        """
        raise NotImplementedError()

    def zero_inputs(self):
        """
        Set all the input ports to 0, useful for intiializing everything to a
        known value
        """
        for name, port in self._circuit.IO.ports.items():
            if port.is_input():
                self.poke(self._circuit.interface.ports[name], 0)

    @property
    def circuit(self):
        return CircuitWrapper(self._circuit, self)

    @abstractmethod
    def wait_until_low(self, signal):
        raise NotImplementedError

    @abstractmethod
    def wait_until_high(self, signal):
        raise NotImplementedError

    def wait_until_negedge(self, signal):
        self.wait_until_high(signal)
        self.wait_until_low(signal)

    def wait_until_posedge(self, signal):
        self.wait_until_low(signal)
        self.wait_until_high(signal)

    def pulse_high(self, signal):
        # first make sure the signal is actually low to begin with
        self.expect(signal, 0)

        # first set the signal high, then bring it low again
        self.poke(signal, 1)
        self.poke(signal, 0)

    def pulse_low(self, signal):
        # first make sure the signal is actually high to begin with
        self.expect(signal, 1)

        # first set the signal low, then bring it high again
        self.poke(signal, 0)
        self.poke(signal, 1)

    def sync_reset(self, active_high=True, cycles=1):
        # assert reset and set clock to zero
        self.poke(self.reset_port, 1 if active_high else 0)
        self.poke(self.clock, 0)

        # wait the desired number of clock cycles
        self.step(2 * cycles)

        # de-assert reset
        self.poke(self.reset_port, 0 if active_high else 1)

    def internal(self, *args):
        # return a SelectPath containing the desired path
        return SelectPath([self.circuit] + list(args))

    def __call__(self, *args, **kwargs):
        """
        Poke the inputs of the circuit using *args (ordered, anonymous input
        reference, excluding clocks) and **kwargs.  **kwargs will overwrite any
        inputs written by *args.

        Evaluate the circuit

        Return the "peeked" output(s) of the circuit (tuple for multiple
        outputs)
        """
        num_args = len(args) + len([value for value in kwargs.values() if not
                                    isinstance(value, m.ClockTypes)])
        defn_outputs = [port for port in self._circuit.interface.outputs()
                        if not isinstance(port, m.ClockTypes)]
        if num_args != len(defn_outputs):
            logging.warning("Number of arguments to __call__ did not match "
                            "number of circuit inputs")
        for arg, port in zip(args, defn_outputs):
            self.poke(port, arg)
        for key, value in kwargs.items():
            self.poke(getattr(self._circuit, key), value)
        self.eval()
        result = tuple(getattr(self.circuit, port) for port in
                       self._circuit.interface.inputs_by_name())
        if len(result) == 1:
            return result[0]
        return result
