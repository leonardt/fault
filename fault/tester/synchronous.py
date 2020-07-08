from .staged_tester import StagedTester
from ..system_verilog_target import SynchronousSystemVerilogTarget
from ..verilator_target import SynchronousVerilatorTarget


class SynchronousTester(StagedTester):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.clock is None:
            raise ValueError("SynchronousTester requires a clock")

    def eval(self):
        raise TypeError("Cannot eval with synchronous tester")

    def advance_cycle(self):
        self.step(2)

    def make_target(self, target, **kwargs):
        if target == "system-verilog":
            return SynchronousSystemVerilogTarget(self._circuit,
                                                  clock=self.clock, **kwargs)
        if target == "system-verilog":
            return SynchronousVerilatorTarget(self._circuit, clock=self.clock,
                                              **kwargs)
        return super().make_target(target, **kwargs)
