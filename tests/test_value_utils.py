import pytest
import magma as m
from hwtypes import BitVector
from fault.array import Array
from fault.value_utils import make_value
from fault.value import AnyValue, UnknownValue


class Foo(m.Circuit):
    io = m.IO(a=m.In(m.Bit),
              b=m.In(m.Bits[8]),
              c=m.In(m.Array[12, m.Bit]),
              d=m.In(m.Array[16, m.Array[20, m.Bit]]))


def test_all():
    # Bit type.
    assert make_value(type(Foo.a), BitVector[1](0)) == BitVector[1](0)
    assert make_value(type(Foo.a), 0) == BitVector[1](0)
    assert make_value(type(Foo.a), 1) == BitVector[1](1)
    assert make_value(type(Foo.a), AnyValue) == AnyValue
    assert make_value(type(Foo.a), UnknownValue) == UnknownValue
    with pytest.raises(NotImplementedError) as pytest_e:
        make_value(type(Foo.a), 2)
        assert False
    assert pytest_e.type == NotImplementedError

    # NOTE(rsetaluri): For the following 3 tests we use arbitray values as input
    # into the bit-vectors. The tests should pass for any number.

    # Bits type.
    assert make_value(type(Foo.b), BitVector[8](5)) == BitVector[8](5)
    assert make_value(type(Foo.b), 17) == BitVector[8](17)
    assert make_value(type(Foo.b), AnyValue) == AnyValue
    assert make_value(type(Foo.b), UnknownValue) == UnknownValue

    # Array(Bit) type. Should be the same as above.
    assert make_value(type(Foo.c), BitVector[12](83)) == BitVector[12](83)
    assert make_value(type(Foo.c), 23) == BitVector[12](23)
    assert make_value(type(Foo.c), AnyValue) == AnyValue
    assert make_value(type(Foo.c), UnknownValue) == UnknownValue

    # Array(Array(Bit)) type.
    assert make_value(type(Foo.d), 894) == Array([BitVector[20](894)] * 16, 16)
    assert make_value(type(Foo.d), AnyValue) == Array([AnyValue] * 16, 16)
    assert make_value(type(Foo.d), UnknownValue) == \
        Array([UnknownValue] * 16, 16)
