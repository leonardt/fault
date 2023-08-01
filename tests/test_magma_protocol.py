from typing import Optional

import pytest

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


class SimpleMagmaProtocolMeta(m.MagmaProtocolMeta):
    _CACHE = {}

    def _to_magma_(cls):
        return cls.T

    def _qualify_magma_(cls, direction):
        return cls[cls.T.qualify(direction)]

    def _flip_magma_(cls):
        return cls[cls.T.flip()]

    def _from_magma_value_(cls, val):
        return cls(val)

    def __getitem__(cls, T):
        try:
            base = cls.base
        except AttributeError:
            base = cls
        dct = {"T": T, "base": base}
        derived = type(cls)(f"{base.__name__}[{T}]", (cls,), dct)
        return SimpleMagmaProtocolMeta._CACHE.setdefault(T, derived)

    def __repr__(cls):
        return str(cls)

    def __str__(cls):
        return cls.__name__


class BrokenProtocol(m.MagmaProtocol, metaclass=SimpleMagmaProtocolMeta):
    def __init__(self, val = None):
        if val is None:
            self._val = self.T()
        elif isinstance(val, self.T):
            self._val = val
        else:
            self._val = self.T(val)

    def _get_magma_value_(self):
        return self._val


class FixedProtocol(BrokenProtocol):
    @property
    def debug_name(self):
        # Beyond not liking the number of names already reserved by
        # MagmaProtocol I have not strong feeling about adding `debug_name`
        # to the list.
        return self._get_magma_value_().debug_name

    def __len__(self):
        # !!! Please do not reserve len !!!
        # I have container types which use it
        cls = type(self)
        magma_t = cls._to_magma_()
        if issubclass(magma_t, m.Digital):
            # for some reason this breaks on m.Bits
            # dont know if bug
            return len(magma_t)
        else:
            return len(self._get_magma_value_())

def gen_DUT(T, BoxT, i, o):
    if i:
        i_t = BoxT[T]
    else:
        i_t = T

    if o:
        o_t = BoxT[T]
    else:
        o_t = T

    class DUT(m.Circuit):
        io = m.IO(
            I=m.In(i_t),
            O=m.Out(o_t)
        )
        if i and not o:
            io.O @= io.I._get_magma_value_()
        elif o and not i:
            io.O @= o_t._from_magma_value_(io.I)
        else:
            io.O @= io.I
    return DUT



@pytest.mark.parametrize('T', [m.Bit, m.Bits[16]])
@pytest.mark.parametrize('BoxT', [BrokenProtocol])
@pytest.mark.parametrize('proto_in, proto_out', [
    (True, False),
    (False, True),
    (True, True),
    ])
def test_protocol_as_input_and_output(T, BoxT, proto_in, proto_out):
    DUT = gen_DUT(T, BoxT, proto_in, proto_out)
    tester = fault.Tester(DUT)
    tester.circuit.I = BoxT[T](T(0))
    tester.eval()
    tester.circuit.O.expect(T(0))
    tester.compile_and_run("verilator")
