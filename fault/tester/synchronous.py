import inspect

from .staged_tester import StagedTester
from ..system_verilog_target import SynchronousSystemVerilogTarget
from ..verilator_target import SynchronousVerilatorTarget

from fault.tester.control import add_control_structures
from fault.pysv import PysvMonitor


@add_control_structures
class SynchronousTester(StagedTester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.clock is None:
            raise ValueError("SynchronousTester requires a clock")

    def eval(self):
        raise TypeError("Cannot eval with synchronous tester")

    def advance_cycle(self):
        for monitor in self.monitors:
            argspec = inspect.getfullargspec(monitor.observe.func_def.func)
            assert argspec.args[0] == "self", "Expected self as first arg"
            args = [self.peek(getattr(self._circuit, arg))
                    for arg in argspec.args[1:]]
            assert argspec.varargs is None, "Unsupported"
            assert argspec.varkw is None, "Unsupported"
            assert argspec.kwonlyargs == [], "Unsupported"
            assert argspec.kwonlydefaults is None, "Unsupported"
            assert argspec.annotations  == {}, "Unsupported"
            assert argspec.defaults is None, "Unsupported"
            self.make_call_stmt(monitor.observe, *args)
        self.step(2)

    def make_target(self, target, **kwargs):
        if target == "system-verilog":
            return SynchronousSystemVerilogTarget(self._circuit,
                                                  clock=self.clock, **kwargs)
        if target == "system-verilog":
            return SynchronousVerilatorTarget(self._circuit, clock=self.clock,
                                              **kwargs)
        return super().make_target(target, **kwargs)

    def attach_monitor(self, monitor: PysvMonitor):
        # TODO: See tests/test_pysv.py:111, pysv preventing inheritance
        # if not isinstance(monitor, PysvMonitor):
        #     raise TypeError("Expected PysvMonitor")
        self.monitors.append(monitor)
