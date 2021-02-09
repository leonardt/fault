
import magma as m
import fault


class MWrapperMeta(m.MagmaProtocolMeta):
    def __getitem__(cls, T):
        assert cls is MWrapper
        return type(cls)(f'MWrapper[{T}]', (cls,), {'_T_': T})

    def _to_magma_(cls):
        return cls._T_

    def _qualify_magma_(cls, d):
        return MWrapper[cls._T_.qualify(d)]

    def _flip_magma_(cls):
        return MWrapper[cls._T_.flip()]

    def _from_magma_value_(cls, value):
        return cls(value)


class MWrapper(m.MagmaProtocol, metaclass=MWrapperMeta):
    def __init__(self, val):
        if not isinstance(val, type(self)._T_):
            raise TypeError()
        self._value_ = val

    def _get_magma_value_(self):
        return self._value_

    def apply(self, f):
        return f(self._value_)


WrappedBits8 = MWrapper[m.UInt[8]]


@m.sequential2()
class Foo:
    def __call__(self, val: WrappedBits8) -> m.UInt[8]:
        return val.apply(lambda x: x + 1)


def test_proto():
    tester = fault.Tester(Foo)
    tester.circuit.val = 1
    tester.eval()
    tester.circuit.O.expect(2)
    tester.compile_and_run("verilator", flags=['-Wno-unused'])
