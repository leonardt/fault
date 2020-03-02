from itertools import product
import pytest
from hwtypes import Bit
import magma as m
import mantle
from fault.test_vectors import (generate_function_test_vectors,
                                generate_simulator_test_vectors)
from fault.value import AnyValue
from .common import TestBasicCircuit, TestArrayCircuit, TestSIntCircuit


@pytest.mark.parametrize("Circuit", [TestBasicCircuit, TestArrayCircuit,
                                     TestSIntCircuit])
def test_circuit(Circuit):
    def fn(I):
        return I
    function_test_vectors = generate_function_test_vectors(Circuit, fn)
    simulator_test_vectors = generate_simulator_test_vectors(Circuit)
    assert function_test_vectors == simulator_test_vectors


def test_combinational_circuit():
    def f(a, b, c):
        return (a & b) ^ c

    class main(m.Circuit):
        io = m.IO(a=m.In(m.Bit),
                  b=m.In(m.Bit),
                  c=m.In(m.Bit),
                  d=m.Out(m.Bit))

        m.wire(f(io.a, io.b, io.c), io.d)

    test_vectors = generate_function_test_vectors(main, f)
    assert len(test_vectors) == 2 ** 3 + 1

    # Check that vectors are as expected. The general pattern that we expect is
    # that the outputs of the ith vector match f() evaluated on the inputs in
    # the (i - 1)th vector. Also the order of the inputs matches the canonical
    # order of the cartesian product.
    for i, inputs in enumerate(product((0, 1), (0, 1), (0, 1))):
        vec = test_vectors[i].test_vector
        expected = [Bit(x) for x in inputs]
        assert vec[:3] == expected
        if i == 0:
            assert vec[3] == AnyValue
            continue
        prev_inputs = test_vectors[i - 1].test_vector[:3]
        expected = Bit(f(*prev_inputs))
        assert vec[3] == expected
    # Checking the pattern above for the last vector.
    vec = test_vectors[-1].test_vector
    prev_inputs = test_vectors[-2].test_vector[:3]
    expected = Bit(f(*prev_inputs))
    assert vec[3] == expected
