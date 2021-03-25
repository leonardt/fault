import inspect

from .staged_tester import StagedTester
from ..system_verilog_target import SynchronousSystemVerilogTarget
from ..verilator_target import SynchronousVerilatorTarget

from fault.tester.control import add_control_structures
from fault.pysv import PysvMonitor
import fault.actions as actions

import magma as m


@add_control_structures
class SynchronousTester(StagedTester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.clock is None:
            raise ValueError("SynchronousTester requires a clock")

    def eval(self):
        raise TypeError("Cannot eval with synchronous tester")

    def _flat_peek(self, value):
        if (isinstance(value, m.Tuple) or
                isinstance(value, m.Array) and
                not issubclass(value.T, m.Digital)):
            return sum((self._flat_peek(elem) for elem in value), [])
        return [self.peek(value)]

    def _call_monitors(self):
        for monitor in self.monitors:
            args = monitor.observe._orig_args_
            assert args[0] == "self"
            args = sum((self._flat_peek(getattr(self._circuit, arg))
                        for arg in args[1:]), [])
            self.make_call_stmt(monitor.observe, *args)

    def advance_cycle(self):
        self.step(1)
        self._call_monitors()
        self.step(1)

    def make_target(self, target, **kwargs):
        if target == "system-verilog":
            return SynchronousSystemVerilogTarget(self._circuit,
                                                  clock=self.clock, **kwargs)
        if target == "system-verilog":
            return SynchronousVerilatorTarget(self._circuit, clock=self.clock,
                                              **kwargs)
        return super().make_target(target, **kwargs)

    def attach_monitor(self, monitor: actions.Var):
        if (not isinstance(monitor, actions.Var) and
                not isinstance(monitor._type, PysvMonitor)):
            raise TypeError("Expected PysvMonitor variable")
        self.monitors.append(monitor)
