import magma
from bit_vector import BitVector
import fault.actions as actions
from fault.verilator_target import VerilatorTarget
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.value_utils import make_value
from fault.value import AnyValue


class TestVectorBuilder:
    def __init__(self, circuit):
        self.circuit = circuit
        self.port_to_index = {}
        for i, port in enumerate(self.circuit.interface.ports.values()):
            self.port_to_index[port] = i
        self.vectors = [self.__empty_vector()]

    def __empty_vector(self):
        ports = self.circuit.interface.ports
        return [make_value(port, AnyValue) for port in ports.values()]

    def __eval(self):
        self.vectors.append(self.vectors[-1].copy())
        for port in self.circuit.interface.ports.values():
            if port.isinput():
                index = self.port_to_index[port]
                self.vectors[-1][index] = make_value(port, AnyValue)

    def process(self, action):
        if isinstance(action, (actions.Poke, actions.Expect)):
            index = self.port_to_index[action.port]
            self.vectors[-1][index] = action.value
        elif isinstance(action, actions.Eval):
            self.__eval()
        elif isinstance(action, actions.Step):
            index = self.port_to_index[action.clock]
            for step in range(action.steps):
                self.__eval()
                self.vectors[-1][index] ^= BitVector(1, 1)
        else:
            raise NotImplementedError(action)


class Tester:
    def __init__(self, circuit, clock=None):
        self.circuit = circuit
        self.actions = []
        if clock is not None and not isinstance(clock, magma.ClockKind):
            raise TypeError(f"Expected clock port: {clock}")
        self.clock = clock

    def make_target(self, target, **kwargs):
        if target == "verilator":
            return VerilatorTarget(self.circuit, self.actions, **kwargs)
        if target == "python":
            return MagmaSimulatorTarget(self.circuit, self.actions,
                                        backend='python', **kwargs)
        if target == "coreir":
            return MagmaSimulatorTarget(self.circuit, self.actions,
                                        backend='coreir', **kwargs)
        raise NotImplementedError(target)

    def poke(self, port, value):
        value = make_value(port, value)
        self.actions.append(actions.Poke(port, value))

    def expect(self, port, value):
        value = make_value(port, value)
        self.actions.append(actions.Expect(port, value))

    def eval(self):
        self.actions.append(actions.Eval())

    def step(self, steps=1):
        if self.clock is None:
            raise RuntimeError("Stepping tester without a clock (did you "
                               "specify a clock during initialization?)")
        self.actions.append(actions.Step(steps, self.clock))

    def serialize(self):
        builder = TestVectorBuilder(self.circuit)
        for action in self.actions:
            builder.process(action)
        return builder.vectors

    def compile_and_run(self, target="verilator", **kwargs):
        target_inst = self.make_target(target, **kwargs)
        target_inst.run()
