from .base import TesterBase
from .utils import get_port_type
import fault
import inspect
import fault
import warnings
import logging
import magma as m
import fault.actions as actions
try:
    from fault.magma_simulator_target import MagmaSimulatorTarget
except ModuleNotFoundError:
    MagmaSimulatorTarget = None
    pass
from fault.vector_builder import VectorBuilder
from fault.value_utils import make_value
from fault.verilator_target import VerilatorTarget
from fault.system_verilog_target import SystemVerilogTarget
from fault.verilogams_target import VerilogAMSTarget
from fault.spice_target import SpiceTarget
from fault.actions import Loop, While, If
from fault.circuit_utils import check_interface_is_subset
from fault.wrapper import PortWrapper
from fault.file import File
from fault.select_path import SelectPath
from ..magma_utils import is_recursive_type
import fault.expression as expression
import os
import inspect
from fault.config import get_test_dir
from typing import List
import tempfile
from hwtypes import BitVector


class Tester(TesterBase):
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

    def __init__(self, circuit: m.Circuit, clock: m.Clock = None,
                 reset: m.Reset = None, poke_delay_default=None,
                 expect_strict_default=True):
        """
        `circuit`: the device under test (a magma circuit)
        `clock`: optional, a port from `circuit` corresponding to the clock
        `reset`: optional, a port from `circuit` corresponding to the reset
        `poke_delay_default`: default time delay after each poke.  if left
        at None, the target-specific default will be used.
        `expect_strict_default`: if True, use strict equality check if
        not specified by the user.
        """
        super().__init__(circuit, clock, reset, poke_delay_default,
                         expect_strict_default)
        self.init_clock()
        self.targets = {}
        # For public verilator modules
        self.verilator_includes = []

    def init_clock(self):
        if self.clock is not None:
            # Default initalize clock to zero (e.g. for SV targets)
            self.poke(self.clock, 0)

    def make_target(self, target: str, **kwargs):
        """
        Called with the string `target`, returns an instance of the
        corresponding target object.

        Supported values of target: "verilator", "coreir", "python",
            "system-verilog", "verilog-ams"
        """
        if target == "verilator":
            return VerilatorTarget(self._circuit, **kwargs)
        elif target == "coreir":
            if MagmaSimulatorTarget is None:
                raise Exception("MagmaSimulatorTarget could not be imported, "
                                "please install coreir/pycoreir")
            return MagmaSimulatorTarget(self._circuit, clock=self.clock,
                                        backend='coreir', **kwargs)
        elif target == "python":
            if MagmaSimulatorTarget is None:
                raise Exception("MagmaSimulatorTarget could not be imported, "
                                "please install coreir/pycoreir")
            return MagmaSimulatorTarget(self._circuit, clock=self.clock,
                                        backend='python', **kwargs)
        elif target == "system-verilog":
            return SystemVerilogTarget(self._circuit, **kwargs)
        elif target == "verilog-ams":
            return VerilogAMSTarget(self._circuit, **kwargs)
        elif target == "spice":
            return SpiceTarget(self._circuit, **kwargs)
        raise NotImplementedError(target)

    def _poke(self, port, value, delay=None):
        if not isinstance(value, (LoopIndex, actions.FileRead,
                                  expression.Expression)):
            type_ = get_port_type(port)
            value = make_value(type_, value)
        self.actions.append(actions.Poke(port, value, delay=delay))

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

    def assert_(self, expr):
        if not isinstance(expr, expression.Expression):
            raise TypeError("Expected instance of Expression")
        self.actions.append(actions.Assert(expr))

    def _expect(self, port, value, strict=None, caller=None, **kwargs):
        # implement expect
        if not isinstance(value, (actions.Peek, PortWrapper, actions.FileRead,
                                  LoopIndex, expression.Expression)):
            type_ = get_port_type(port)
            value = make_value(type_, value)
        self.actions.append(actions.Expect(port=port, value=value,
                                           strict=strict, caller=caller,
                                           **kwargs))

    def eval(self):
        """
        Evaluate the DUT given the current input port values
        """
        self.actions.append(actions.Eval())

    def delay(self, time):
        """
        Wait the specified amount of time before proceeding
        """
        self.actions.append(actions.Delay(time=time))

    def get_value(self, port):
        """
        Returns an object with a "value" property that will
        be filled after the simulation completes.
        """
        action = actions.GetValue(port=port)
        self.actions.append(action)
        return action

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

    def _make_directory(self, directory):
        """
        Handles support for `set_test_dir('callee_file_dir')`

        When configured in this mode, fault will generate the test
        collateral treating `directory` as relative to the file calling
        `compile_and_run` or `compile`.

        The default behvaior is to generate the collateral relative to where
        Python is invoked.
        """
        if get_test_dir() == 'callee_file_dir':
            (_, filename, _, _, _, _) = inspect.getouterframes(
                inspect.currentframe())[2]
            file_path = os.path.abspath(os.path.dirname(filename))
            directory = os.path.join(file_path, directory)
        return directory

    def _compile(self, target="verilator", **kwargs):
        """
        Create an instance of the target backend.

        For the verilator backend, this will run verilator to compile the C++
        model.  This allows the user to separate the logic to compile the DUT
        into the model and run the actual tests (for example, if the user
        wants to compile a DUT once and run multiple tests with the same model,
        this avoids having to call verilator multiple times)
        """
        self.targets[target] = self.make_target(target, **kwargs)

    def compile(self, target="verilator", **kwargs):
        """
        Logic deferred to `_compile` method, one level of indirection in order
        to avoid calling `_make_directory` twice in `compile` and
        `compile_and_run`
        """
        if "directory" in kwargs:
            kwargs["directory"] = self._make_directory(kwargs["directory"])
        self._compile(target, **kwargs)

    def run(self, target="verilator"):
        """
        Run the current action sequence using the specified `target`.  The user
        should call `compile` with `target` before calling `run`.
        """
        # Try to get the target
        try:
            target_obj = self.targets[target]
        except KeyError:
            raise Exception(f"Could not find target={target}, did you compile it first?")  # noqa

        # Run the target, possibly passing in some custom arguments
        logging.info("Running tester...")
        if target == "verilator":
            target_obj.run(self.actions, self.verilator_includes)
        else:
            target_obj.run(self.actions)
        logging.info("Success!")

    def _compile_and_run(self, target="verilator", **kwargs):
        """
        Compile and run the current action sequence using `target`, assuming
        that the build directory already exists (this allow for some
        in using temporary vs. persistent directories)
        """
        self._compile(target, **kwargs)
        self.run(target)

    def compile_and_run(self, target="verilator", tmp_dir=False, **kwargs):
        """
        Compile and run the current action sequence using `target`, making
        a build directory if needed.  This is the function that should be
        called directly by the user.
        """
        if tmp_dir:
            with tempfile.TemporaryDirectory(dir='.') as directory:
                kwargs['directory'] = directory
                self._compile_and_run(target=target, **kwargs)
        else:
            if 'directory' in kwargs:
                kwargs['directory'] = self._make_directory(kwargs['directory'])
            self._compile_and_run(target=target, **kwargs)

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

    def loop(self, n_iter):
        """
        Returns a new tester to record actions inside the loop.  The created
        loop action object maintains a references to the return Tester's
        `actions` list.
        """
        loop_tester = LoopTester(self._circuit, self.clock)
        self.actions.append(Loop(n_iter, loop_tester.index,
                                 loop_tester.actions))
        return loop_tester

    def file_open(self, file_name, mode="r", chunk_size=1, endianness="little"):
        """
        mode : "r" for read, "w" for write
        chunk_size : number of bytes per read/write
        """
        file = File(file_name, self, mode, chunk_size, endianness)
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

    def _while(self, cond):
        """
        Returns a new tester to record actions inside the loop.  The created
        loop action object maintains a references to the return Tester's
        `actions` list.
        """
        while_tester = LoopTester(self._circuit, self.clock)
        self.actions.append(While(cond, while_tester.actions))
        return while_tester

    def _if(self, cond):
        if_tester = IfTester(self._circuit, self.clock)
        self.actions.append(If(cond, if_tester.actions,
                               if_tester.else_actions))
        return if_tester

    def file_scanf(self, file, _format, *args):
        self.actions.append(actions.FileScanFormat(file, _format, *args))

    def Var(self, name, _type):
        var = actions.Var(name, _type)
        self.actions.append(var)
        return var

    def wait_on(self, cond):
        loop = self._while(cond)
        loop.step()

    def wait_until_low(self, signal):
        self.wait_on(self.peek(signal) != 0)

    def wait_until_high(self, signal):
        self.wait_on(self.peek(signal) == 0)

    def wait_until_negedge(self, signal):
        self.wait_until_high(signal)
        self.wait_until_low(signal)

    def wait_until_posedge(self, signal, steps_per_iter=1):
        self.wait_until_low(signal)
        self.wait_until_high(signal)


class LoopIndex:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class NoClockInit:
    """
    Sub testers should not initialize the clock
    """

    def init_clock(self):
        pass


class LoopTester(NoClockInit, Tester):
    __unique_index_id = -1

    def __init__(self, circuit: m.Circuit, clock: m.Clock = None):
        super().__init__(circuit, clock)
        LoopTester.__unique_index_id += 1
        self.index = LoopIndex(
            f"__fault_loop_var_action_{LoopTester.__unique_index_id}")


class ElseTester(NoClockInit, Tester):
    def __init__(self, else_actions: List, circuit: m.Circuit,
                 clock: m.Clock = None):
        super().__init__(circuit, clock)
        self.actions = else_actions


class IfTester(NoClockInit, Tester):
    def __init__(self, circuit: m.Circuit, clock: m.Clock = None):
        super().__init__(circuit, clock)
        self.else_actions = []

    def _else(self):
        return ElseTester(self.else_actions, self._circuit, self.clock)


StagedTester = Tester
