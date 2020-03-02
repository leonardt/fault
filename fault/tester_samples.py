import fault
from abc import ABCMeta, abstractmethod


class GenericCellTester(fault.Tester, metaclass=ABCMeta):
    def __init__(self, circuit, *args, n_trials=100, supply0='vss',
                 supply1='vdd', poke_delay_default=100e-9, **kwargs):
        # call super constructor
        super().__init__(circuit, *args, poke_delay_default=poke_delay_default,
                         **kwargs)

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

    @abstractmethod
    def define_trial(self):
        pass

    def define_test(self):
        self.define_init()
        for _ in range(self.n_trials):
            self.define_trial()


class SingleOutputTester(GenericCellTester):
    def __init__(self, circuit, *args, inputs=None, out='out', **kwargs):
        # save settings
        self.inputs = inputs if inputs is not None else []
        self.out = out

        # call super constructor
        super().__init__(circuit, *args, **kwargs)

    @abstractmethod
    def model(self, *args):
        pass

    def define_trial(self):
        # poke random data
        data = []
        for input_ in self.inputs:
            data += [fault.random_bit()]
            self.poke(input_, data[-1])
        # expect a value based on the model
        self.expect(self.out, self.model(*data), strict=True)


class UnaryOpTester(SingleOutputTester):
    def __init__(self, *args, in_='in_', out='out', **kwargs):
        inputs = [in_]
        super().__init__(*args, inputs=inputs, out=out, **kwargs)


class BinaryOpTester(SingleOutputTester):
    def __init__(self, *args, a='a', b='b', out='out', **kwargs):
        inputs = [a, b]
        super().__init__(*args, inputs=inputs, out=out, **kwargs)


class InvTester(UnaryOpTester):
    def model(self, in_):
        return not in_


class BufTester(UnaryOpTester):
    def model(self, in_):
        return in_


class NandTester(BinaryOpTester):
    def model(self, a, b):
        return not (a and b)


class NorTester(BinaryOpTester):
    def model(self, a, b):
        return not (a or b)


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
        self.poke(self.lbl, 0)
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
