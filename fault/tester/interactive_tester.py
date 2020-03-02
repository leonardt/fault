import magma as m
from magma.simulator import PythonSimulator
from magma.scope import Scope
from .abstract_tester import AbstractTester
from ..select_path import SelectPath
from ..value_utils import make_value
from hwtypes import BitVector, Bit
from ..wrapper import PortWrapper


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
        self.simulator = PythonSimulator(self._circuit)

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

    def set_value(self, port, value):
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
        value = make_value(type_, value)
        self.set_value(port, value)

    def get_value(self, port):
        port, scope = self.process_port(port)
        if isinstance(port, (int, BitVector, Bit, list)):
            return port
        return self.simulator.get_value(port, scope)

    def expect(self, port, value):
        got = self.get_value(port)
        expected = self.get_value(value)
        check(got, port, expected)
