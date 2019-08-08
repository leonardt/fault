import fault
import random

class SRAMTester(fault.Tester):
    def __init__(self, circuit, *args, n_trials=100, prob1=0.5, **kwargs):
        # call super constructor
        super().__init__(circuit, *args, **kwargs)

        # save settings
        self.n_trials = n_trials
        self.prob1 = prob1

        # define the test
        self.define_test()

    def define_test(self):
        # initialize pin values
        self.poke(self._circuit.wl, 0)
        self.poke(self._circuit.lbl, 0)
        self.poke(self._circuit.lblb, 0)
        if hasattr(self.circuit, 'vdd'):
            self.poke(self._circuit.vdd, 1)
        if hasattr(self.circuit, 'vss'):
            self.poke(self._circuit.vss, 0)

        for _ in range(self.n_trials):
            # generate random input
            d = random.random() < self.prob1

            # write value
            self.poke(self._circuit.lbl, d)
            self.poke(self._circuit.lblb, not d)
            self.poke(self._circuit.wl, 1)
            self.poke(self._circuit.wl, 0)

            # read value
            self.poke(self._circuit.lbl, fault.HiZ)
            self.poke(self._circuit.lblb, fault.HiZ)
            self.poke(self._circuit.wl, 1)
            self.expect(self._circuit.lbl, d, strict=True)
            self.expect(self._circuit.lblb, not d, strict=True)
            self.poke(self._circuit.wl, 0)
