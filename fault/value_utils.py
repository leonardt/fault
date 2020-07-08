import fault
import magma
import magma as m
from magma.protocol_type import MagmaProtocol
from hwtypes import BitVector, Bit, FPVector
from fault.value import AnyValue, UnknownValue, HiZ
from fault.ms_types import RealType
from fault.array import Array
from fault.select_path import SelectPath
from hwtypes.adt import Enum


def make_value(type_, value):
    if isinstance(type_, m.MagmaProtocolMeta):
        type_ = type_._to_magma_()
    if isinstance(value, MagmaProtocol):
        value = value._get_magma_value_()
        if not value.const():
            raise TypeError("Expected const value when poking with instance of "
                            "MagmaProtocol")
    if issubclass(type_, RealType):
        return make_real(value)
    if issubclass(type_, magma.Digital):
        return make_bit(value)
    if issubclass(type_, magma.Array):
        return make_array(type_.T, type_.N, value)
    if issubclass(type_, magma.Tuple):
        raise NotImplementedError()
    raise NotImplementedError(type_, value)


def make_real(value):
    return value


def make_bit(value):
    # TODO(rsetaluri): Use bit_vector.Bit when implemented.
    if isinstance(value, BitVector) and len(value) == 1:
        return value[0]
    if value == 0 or value == 1:
        return Bit(value)
    if value is AnyValue or value is UnknownValue or value is HiZ:
        return value
    raise NotImplementedError(value)


def make_array(T, N, value):
    assert isinstance(N, int)
    if issubclass(T, magma.Digital):
        return make_bit_vector(N, value)
    if issubclass(T, magma.Array):
        if isinstance(value, list):
            return Array([make_array(T.T, T.N, value[i]) for i in range(N)], N)
        else:
            return Array([make_array(T.T, T.N, value) for _ in range(N)], N)
    raise NotImplementedError(T, N, value)


def make_bit_vector(N, value):
    assert isinstance(N, int)
    if isinstance(value, FPVector):
        value = value.reinterpret_as_bv()
    if isinstance(value, BitVector[N]):
        return value
    if isinstance(value, BitVector) and len(value) < N or \
            isinstance(value, Bit):
        return BitVector[N](value)
    if isinstance(value, int):
        return BitVector[N](value)
    if value is AnyValue or value is UnknownValue or value is HiZ:
        return value
    if isinstance(value, Enum):
        return BitVector[N](value.value)
    if isinstance(value, m.Bits):
        return BitVector[N](int(value))
    raise NotImplementedError(N, value, type(value))


def is_any(value):
    if value is AnyValue:
        return True
    if isinstance(value, list):
        return all([is_any(v) for v in value])
    return False
