import magma as m
import fault.actions as actions
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.logging import warning
from fault.vector_builder import VectorBuilder
from fault.value_utils import make_value
from fault.verilator_target import VerilatorTarget
from fault.system_verilog_target import SystemVerilogTarget
from fault.actions import Poke, Expect, Step, Print, Loop
from fault.circuit_utils import check_interface_is_subset
from fault.wrapper import CircuitWrapper, PortWrapper, InstanceWrapper
from fault.file import File
import copy


class Tester:
    """
    The fault `Tester` object provides a mechanism in Python to construct tests
    for magma circuits.  The `Tester` is instantiated with a specific magma
    circuit and provides an API for performing actions on the circuit
    interface.

    ## Actions
        * tester_inst.poke(port, value) - set `port` to be `value`
        * tester_inst.eval() - have the backend simulator evaluate the DUT to
            propogate any poked inputs (this happens implicitly on every poke
            for event driven simulators such as ncsim/vcs, but not for
            verilator)
        * tester_inst.expect(port, value) - expect `port` to equal `value`
        * tester_inst.peek(port) - returns a symbolic handle to the port's
            current value (current in the context of the tester_inst's recorded
            action sequence)
        * tester_inst.step(n) - Step the clock `n` times (defaults to 1)
        * tester_inst.print(port) - Print out the value of `port`


    Tester supports multiple simulation environments (backends) for the actual
    execution of tests.

    ## Backend Targets
        * verilator
        * ncsim
        * vcs
    """

    __test__ = False  # Tell pytest to skip this class for discovery

    def __init__(self, circuit: m.Circuit, clock: m.ClockType = None):
        """
        `circuit`: the device under test (a magma circuit)
        `clock`: optional, a port from `circuit` corresponding to the clock
        """
        self._circuit = circuit
        self.actions = []
        if clock is not None and not isinstance(clock, m.ClockType):
            raise TypeError(f"Expected clock port: {clock, type(clock)}")
        self.clock = clock
        self.targets = {}
        # For public verilator modules
        self.verilator_includes = []

    def make_target(self, target: str, **kwargs):
        """
        Called with the string `target`, returns an instance of the
        corresponding target object.

        Supported values of target: "verilator", "coreir", "python",
            "system-verilog"
        """
        if target == "verilator":
            return VerilatorTarget(self._circuit, **kwargs)
        elif target == "coreir":
            return MagmaSimulatorTarget(self._circuit, clock=self.clock,
                                        backend='coreir', **kwargs)
        elif target == "python":
            return MagmaSimulatorTarget(self._circuit, clock=self.clock,
                                        backend='python', **kwargs)
        elif target == "system-verilog":
            return SystemVerilogTarget(self._circuit, **kwargs)
        raise NotImplementedError(target)

    def poke(self, port, value):
        """
        Set `port` to be `value`
        """
        if isinstance(port, m.TupleType):
            for p, v in zip(port, value):
                self.poke(p, v)
        else:
            if not isinstance(value, (LoopIndex, actions.FileRead)):
                value = make_value(port, value)
            self.actions.append(actions.Poke(port, value))

    def peek(self, port):
        """
        Returns a symbolic handle to the current value of `port`
        """
        return actions.Peek(port)

    def print(self, format_str, *args):
        """
        Prints out `format_str`

        `*args` should be a variable number of magma ports used to fill in the
        format string
        """
        self.actions.append(actions.Print(format_str, *args))

    def expect(self, port, value):
        """
        Expect the current value of `port` to be `value`
        """
        if not isinstance(value, (actions.Peek, PortWrapper, LoopIndex)):
            value = make_value(port, value)
        self.actions.append(actions.Expect(port, value))

    def eval(self):
        """
        Evaluate the DUT given the current input port values
        """
        self.actions.append(actions.Eval())

    def step(self, steps=1):
        """
        Step the clock `steps` times.
        """
        if self.clock is None:
            raise RuntimeError("Stepping tester without a clock (did you "
                               "specify a clock during initialization?)")
        self.actions.append(actions.Step(self.clock, steps))

    def serialize(self):
        """
        Serialize the action sequence into a set of test vectors
        """
        builder = VectorBuilder(self._circuit)
        for action in self.actions:
            builder.process(action)
        return builder.vectors

    def compile(self, target="verilator", **kwargs):
        """
        Create an instance of the target backend.

        For the verilator backend, this will run verilator to compile the C++
        model.  This allows the user to separate the logic to compile the DUT
        into the model and run the actual tests (for example, if the user
        wants to compile a DUT once and run multiple tests with the same model,
        this avoids having to call verilator multiple times)
        """
        self.targets[target] = self.make_target(target, **kwargs)

    def run(self, target="verilator"):
        """
        Run the current action sequence using the specified `target`.  The user
        should call `compile` with `target` before calling `run`.
        """
        try:
            if target == "verilator":
                self.targets[target].run(self.actions, self.verilator_includes)
            else:
                self.targets[target].run(self.actions)
        except KeyError:
            raise Exception(f"Could not find target={target}, did you compile"
                            " it first?")

    def compile_and_run(self, target="verilator", **kwargs):
        """
        Compile and run the current action sequence using `target`
        """
        self.compile(target, **kwargs)
        self.run(target)

    def retarget(self, new_circuit, clock=None):
        """
        Generates a new instance of the Tester object that targets
        `new_circuit`. This allows you to copy a set of actions for a new
        circuit with the same interface (or an interface that is a super set of
        self._circuit)
        """
        # Check that the interface of self._circuit is a subset of new_circuit
        check_interface_is_subset(self._circuit, new_circuit)

        new_tester = Tester(new_circuit, clock)
        new_tester.actions = [action.retarget(new_circuit, clock) for action in
                              self.actions]
        return new_tester

    def zero_inputs(self):
        """
        Set all the input ports to 0, useful for intiializing everything to a
        known value
        """
        for name, port in self._circuit.IO.ports.items():
            if port.isinput():
                self.poke(self._circuit.interface.ports[name], 0)

    def clear(self):
        """
        Reset the tester by removing any existing actions. Useful for reusing a
        Tester (e.g. one with verilator already compiled).
        """
        self.actions = []

    def __str__(self):
        """
        Returns a string containing a list of the recorded actions stored in
        `self.actions`
        """
        s = object.__str__(self) + "\n"
        s += "Actions:\n"
        for i, action in enumerate(self.actions):
            s += f"    {i}: {action}\n"
        return s

    def verilator_include(self, module_name):
        self.verilator_includes.append(module_name)

    @property
    def circuit(self):
        return CircuitWrapper(self._circuit, self)

    def loop(self, n_iter):
        """
        Returns a new tester to record actions inside the loop.  The created
        loop action object maintains a references to the return Tester's
        `actions` list.
        """
        loop_tester = LoopTester(self.circuit, self.clock)
        self.actions.append(Loop(n_iter, loop_tester.index,
                                 loop_tester.actions))
        return loop_tester

    def file_open(self, file_name, mode="r", chunk_size=1):
        """
        mode : "r" for read, "w" for write
        chunk_size : number of bytes per read/write
        """
        file = File(file_name, self, mode, chunk_size)
        self.actions.append(actions.FileOpen(file))
        return file

    def file_close(self, file):
        self.actions.append(actions.FileClose(file))

    def file_read(self, file):
        read_action = actions.FileRead(file)
        self.actions.append(read_action)
        return read_action

    def file_write(self, file, value):
        self.actions.append(actions.FileWrite(file, value))


class LoopIndex:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class LoopTester(Tester):
    __unique_index_id = -1

    def __init__(self, circuit: m.Circuit, clock: m.ClockType = None):
        super().__init__(circuit, clock)
        LoopTester.__unique_index_id += 1
        self.index = LoopIndex(
            f"__fault_loop_var_action_{LoopTester.__unique_index_id}")
