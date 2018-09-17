import magma
import fault.actions as actions
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.logging import warning
from fault.vector_builder import VectorBuilder
from fault.value_utils import make_value
from fault.verilator_target import VerilatorTarget
from fault.actions import Poke, Expect, Step, Print
from fault.circuit_utils import check_interface_is_subset
import copy


class Tester:
    def __init__(self, circuit, clock=None, default_print_format_str="%x"):
        self.circuit = circuit
        self.actions = []
        if clock is not None and not isinstance(clock, magma.ClockType):
            raise TypeError(f"Expected clock port: {clock, type(clock)}")
        self.clock = clock
        self.default_print_format_str = default_print_format_str

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

    def print(self, port, format_str=None):
        if format_str is None:
            format_str = self.default_print_format_str
        self.actions.append(actions.Print(port, format_str))

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

    def retarget(self, new_circuit, clock=None):
        """
        Generates a new instance of the Tester object that targets
        `new_circuit`. This allows you to copy a set of actions for a new
        circuit with the same interface (or an interface that is a super set of
        self.circuit)
        """
        # Check that the interface of self.circuit is a subset of new_circuit
        check_interface_is_subset(self.circuit, new_circuit)

        new_tester = Tester(new_circuit, clock, self.default_print_format_str)
        new_tester.actions = [action.retarget(new_circuit, clock) for action in
                              self.actions]
        return new_tester

    def zero_inputs(self):
        for name, port in self.circuit.IO.ports.items():
            if port.isinput():
                self.poke(self.circuit.interface.ports[name], 0)
