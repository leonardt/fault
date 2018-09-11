import magma
import fault.actions as actions
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.logging import warning
from fault.vector_builder import VectorBuilder
from fault.value_utils import make_value
from fault.verilator_target import VerilatorTarget
from fault.actions import Poke, Expect, Step
import copy


class Tester:
    def __init__(self, circuit, clock=None):
        self.circuit = circuit
        self.actions = []
        if clock is not None and not isinstance(clock, magma.ClockType):
            raise TypeError(f"Expected clock port: {clock, type(clock)}")
        self.clock = clock

    def make_target(self, target, **kwargs):
        if target == "verilator":
            return VerilatorTarget(self.circuit, self.actions, **kwargs)
        if target == "coreir":
            return MagmaSimulatorTarget(self.circuit, self.actions,
                                        clock=self.clock, backend='coreir',
                                        **kwargs)
        if target == "python":
            warning("Python simulator is not actively supported")
            return MagmaSimulatorTarget(self.circuit, self.actions,
                                        clock=self.clock, backend='python',
                                        **kwargs)
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
        self.actions.append(actions.Step(self.clock, steps))

    def serialize(self):
        builder = VectorBuilder(self.circuit)
        for action in self.actions:
            builder.process(action)
        return builder.vectors

    def compile_and_run(self, target="verilator", **kwargs):
        target_inst = self.make_target(target, **kwargs)
        target_inst.run()

    def __check_interfaces_match(self, old_circuit, new_circuit):
        old_port_names = old_circuit.interface.ports.keys()
        for name in old_port_names:
            if not hasattr(new_circuit, name):
                raise ValueError(f"New circuit does not have port {name}")
            old_kind = type(type(getattr(old_circuit, name)))
            new_kind = type(type(getattr(new_circuit, name)))
            if not (issubclass(new_kind, old_kind) or
                    issubclass(old_kind, new_kind)):
                raise ValueError("Types don't match")

    def copy(self, new_circuit, clock=None):
        """
        Generates a copy of the tester for new_circuit
        Checks that new_circut has exactly the same interface as self.circuit
        """
        self.__check_interfaces_match(self.circuit, new_circuit)
        new_tester = Tester(new_circuit, clock)
        for old_action in self.actions:
            new_action = copy.copy(old_action)
            if isinstance(new_action, (Poke, Expect)):
                new_action.port = getattr(new_circuit,
                                          str(old_action.port.name))
            elif isinstance(new_action, Step):
                new_action.clock = clock
            new_tester.actions.append(new_action)
        return new_tester
