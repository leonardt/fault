import magma
from bit_vector import BitVector
from fault.value import AnyValue, UnknownValue
from fault.array import Array


def make_value(port, value):
    if isinstance(port, (magma._BitType, magma._BitKind)):
        return make_bit(value)
    if isinstance(port, (magma.ArrayType, magma.ArrayKind)):
        return make_array(port.T, port.N, value)
    raise NotImplementedError(port, value)


def make_bit(value):
    # TODO(rsetaluri): Use bit_vector.Bit when implemented.
    if isinstance(value, BitVector) and value.num_bits == 1:
        return value
    if value == 0 or value == 1:
        return BitVector(value, 1)
    if value is AnyValue or value is UnknownValue:
        return value
    raise NotImplementedError(value)


def make_array(T, N, value):
    assert isinstance(N, int)
    if isinstance(T, magma._BitKind):
        return make_bit_vector(N, value)
    if isinstance(T, magma.ArrayKind):
        if isinstance(value, list):
            return Array([make_array(T.T, T.N, value[i]) for i in range(N)], N)
        else:
            return Array([make_array(T.T, T.N, value) for _ in range(N)], N)
    raise NotImplementedError(T, N, value)


def make_bit_vector(N, value):
    assert isinstance(N, int)
    if isinstance(value, BitVector) and N == value.num_bits:
        return value
    if isinstance(value, int):
        return BitVector(value, N)
    if value is AnyValue or value is UnknownValue:
        return value
    raise NotImplementedError(N, value)


def is_any(value):
    if value is AnyValue:
        return True
    if isinstance(value, list):
        return all([is_any(v) for v in value])
    return False
