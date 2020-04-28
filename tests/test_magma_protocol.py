from typing import Optional
import magma as m
import fault
from hwtypes import BitVector


def test_foo_type_magma_protocol():
    class FooMeta(m.MagmaProtocolMeta):
        def _to_magma_(cls):
            return cls.T

        def _qualify_magma_(cls, direction: m.Direction):
            return cls[cls.T.qualify(direction)]

        def _flip_magma_(cls):
            return cls[cls.T.flip()]

        def _from_magma_value_(cls, val: m.Type):
            return cls(val)

        def __getitem__(cls, T):
            return type(cls)(f"Foo{T}", (cls, ), {"T": T})

    class Foo(m.MagmaProtocol, metaclass=FooMeta):
        def __init__(self, val: Optional[m.Type] = None):
            if val is None:
                val = self.T()
            self._val = val

        def _get_magma_value_(self):
            return self._val

        def non_standard_operation(self):
            v0 = self._val << 2
            v1 = m.bits(self._val[0], len(self.T)) << 1
            return Foo(v0 | v1 | m.bits(self._val[0], len(self.T)))

    class Bar(m.Circuit):
        io = m.IO(foo=m.In(Foo[m.Bits[8]]), O=m.Out(m.Bits[8]))
        m.wire(io.foo.non_standard_operation(), io.O)

    tester = fault.Tester(Bar)
    tester.circuit.foo = Foo(m.Bits[8](0xDE))
    tester.eval()
    tester.circuit.O.expect(BitVector[8](0xDE << 2) |
                            (BitVector[8](0xDE) << 1)[0] |
                            BitVector[8](0xDE)[0])
    tester.compile_and_run("verilator")
