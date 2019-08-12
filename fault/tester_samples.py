import fault


class GenericCellTester(fault.Tester):
    def __init__(self, circuit, *args, n_trials=100, supply0='vss',
                 supply1='vdd', **kwargs):
        # call super constructor
        super().__init__(circuit, *args, **kwargs)

        # save settings
        self.supply0 = supply0
        self.supply1 = supply1
        self.n_trials = n_trials

        # define the test
        self.define_test()

    def has_pin(self, name):
        return hasattr(self._circuit, name)

    def poke(self, name, *args, **kwargs):
        super().poke(getattr(self._circuit, name), *args, **kwargs)

    def poke_optional(self, name, *args, **kwargs):
        if self.has_pin(name):
            self.poke(name, *args, **kwargs)

    def expect(self, name, *args, **kwargs):
        super().expect(getattr(self._circuit, name), *args, **kwargs)

    def define_init(self):
        self.poke_optional(self.supply1, 1)
        self.poke_optional(self.supply0, 0)

    def define_trial(self):
        pass

    def define_test(self):
        self.define_init()
        for _ in range(self.n_trials):
            self.define_trial()


class UnaryOpTester(GenericCellTester):
    def __init__(self, circuit, *args, in_='in_', out='out', **kwargs):
        # build the pinmap
        self.in_ = in_
        self.out = out

        # call super constructor
        super().__init__(circuit, *args, **kwargs)


class InvTester(UnaryOpTester):
    def define_trial(self):
        d = fault.random_bit()
        self.poke(self.in_, d)
        self.expect(self.out, not d, strict=True)


class BufTester(UnaryOpTester):
    def define_trial(self):
        d = fault.random_bit()
        self.poke(self.in_, d)
        self.expect(self.out, d, strict=True)


class SRAMTester(GenericCellTester):
    def __init__(self, circuit, *args, lbl='lbl', lblb='lblb', wl='wl',
                 **kwargs):
        # build the pinmap
        self.lbl = lbl
        self.lblb = lblb
        self.wl = wl

        # call super constructor
        super().__init__(circuit, *args, **kwargs)

    def define_init(self):
        self.poke(self.wl, 0)
        self.poke(self.lblb, 0)
        self.poke(self.lblb, 0)
        super().define_init()

    def define_trial(self):
        # generate random input
        d = fault.random_bit()

        # write value
        self.poke(self.lbl, d)
        self.poke(self.lblb, not d)
        self.poke(self.wl, 1)
        self.poke(self.wl, 0)

        # read value
        self.poke(self.lbl, fault.HiZ)
        self.poke(self.lblb, fault.HiZ)
        self.poke(self.wl, 1)
        self.expect(self.lbl, d, strict=True)
        self.expect(self.lblb, not d, strict=True)
        self.poke(self.wl, 0)
