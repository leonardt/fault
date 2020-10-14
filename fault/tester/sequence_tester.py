from fault.tester.staged_tester import Tester


class SequenceTester(Tester):
    def __init__(self, circuit, driver, monitor, sequence, clock=None):
        super().__init__(circuit, clock)
        self.driver = driver
        self.driver.set_tester(self)
        self.monitor = monitor
        self.monitor.set_tester(self)
        self.sequence = sequence

    def _compile_sequences(self):
        for item in self.sequence:
            self.driver.consume(*item)
            if self.clock is None:
                self.eval()
            else:
                self.step(2)
            self.monitor.observe(*item)

    def _compile(self, target="verilator", **kwargs):
        self._compile_sequences()
        super()._compile(target, **kwargs)


class Driver:
    def set_tester(self, tester):
        self.tester = tester


class Monitor:
    def set_tester(self, tester):
        self.tester = tester
