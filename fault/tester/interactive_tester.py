import magma as m
from magma.simulator import PythonSimulator
from magma.scope import Scope
from .abstract_tester import AbstractTester
from ..select_path import SelectPath
from ..value_utils import make_value
from hwtypes import BitVector, Bit
from ..wrapper import PortWrapper
from ..magma_utils import is_recursive_type


class InteractiveTester(AbstractTester):
    pass


def check(got, port, expected):
    if isinstance(port, m.Array) and \
            isinstance(port.T, m.Digital) and \
            not isinstance(port, m.Bits) and \
            isinstance(expected, BitVector):
        # If port is an Array(N, Bit) and **not** a Bits(N), then the
        # Python simulator will return a list of bools. So, if the user
        # provided a BitVector, we unpack it here so the equality check
        # works
        expected = expected.as_bool_list()
    if isinstance(port, m.Array):
        for i in range(port.N):
            check(got[i], port[i], expected[i])
        return
    assert got == expected, f"Got {got}, expected {expected}"


class PythonTester(AbstractTester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.simulator = PythonSimulator(self._circuit, self.clock)

    def eval(self):
        self.simulator.evaluate()

    def process_port(self, port):
        scope = Scope()
        if isinstance(port, PortWrapper):
            port = port.select_path
        if isinstance(port, SelectPath):
            for i in port[1:-1]:
                scope = Scope(parent=scope, instance=i.instance)
            port = port[-1]
        return port, scope

    def _set_value(self, port, value):
        port, scope = self.process_port(port)
        self.simulator.set_value(port, value, scope)

    def poke(self, port, value, delay=None):
        if delay is not None:
            raise NotImplementedError("delay is not support in Python "
                                      "simulator")
        recursed = super().poke(port, value, delay)
        if recursed:
            return
        type_ = self.get_port_type(port)
        self._set_value(port, value)

    def process_result(self, type_, result):
        if issubclass(type_, m.Digital):
            return Bit(result)
        if issubclass(type_, m.Bits):
            return BitVector[len(type_)](result)
        if is_recursive_type(type_):
            return BitVector[len(type_)](result)
        return result

    def _get_value(self, port):
        port, scope = self.process_port(port)
        if isinstance(port, (int, BitVector, Bit, list)):
            return port
        result = self.simulator.get_value(port, scope)
        return self.process_result(type(port), result)

    def expect(self, port, value, strict=None, caller=None, **kwargs):
        recursed = super().expect(port, value, strict, caller, **kwargs)
        if recursed:
            return
        got = self._get_value(port)
        port, scope = self.process_port(port)
        value = make_value(type(port), value)
        expected = self._get_value(value)
        check(got, port, expected)

    def peek(self, port):
        return self._get_value(port)

    def print(self, format_str, *args):
        got = [self._get_value(port) for port in args]
        values = ()
        for value, port in zip(got, args):
            if isinstance(port, m.Array) and \
                    issubclass(port.T, m.Digital):
                value = BitVector[len(port)](value).as_uint()
            elif isinstance(port, m.Array):
                raise NotImplementedError("Printing complex nested"
                                          " arrays")
            values += (value, )
        print(format_str % values, end="")

    def assert_(self, expr, msg=""):
        assert expr, msg

    def delay(self, time):
        raise NotImplementedError()

    def get_value(self, port):
        raise NotImplementedError()

    def step(self, steps=1):
        """
        Step the clock `steps` times.
        """
        self.eval()
        self.simulator.advance(steps)

    def wait_until_low(self, signal):
        while self.peek(signal):
            self.step()

    def wait_until_high(self, signal):
        while ~self.peek(signal):
            self.step()
