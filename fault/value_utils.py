import fault
import magma
from hwtypes import BitVector, Bit
from fault.value import AnyValue, UnknownValue, HiZ
from fault.real_type import RealType, RealKind
from fault.array import Array
from fault.select_path import SelectPath
from hwtypes.adt import Enum


def make_value(port, value):
    switch = port
    if isinstance(switch, SelectPath):
        switch = switch[-1]
    if isinstance(switch, fault.WrappedVerilogInternalPort):
        switch = switch.type_
    if issubclass(switch, RealType):
        return make_real(value)
    if issubclass(switch, magma.Digital):
        return make_bit(value)
    if issubclass(switch, magma.Array):
        return make_array(switch.T, switch.N, value)
    if issubclass(switch, magma.Tuple):
        raise NotImplementedError()
    raise NotImplementedError(switch, value)


def make_real(value):
    return value


def make_bit(value):
    # TODO(rsetaluri): Use bit_vector.Bit when implemented.
    if isinstance(value, BitVector) and len(value) == 1:
        return value
    if value == 0 or value == 1:
        return BitVector[1](value)
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
    raise NotImplementedError(N, value, type(value))


def is_any(value):
    if value is AnyValue:
        return True
    if isinstance(value, list):
        return all([is_any(v) for v in value])
    return False
