from fault.test_vectors import generate_function_test_vectors, \
    generate_simulator_test_vectors
from common import TestBasicCircuit, TestArrayCircuit
import pytest


@pytest.mark.parametrize("Circuit", [TestBasicCircuit, TestArrayCircuit])
def test_circuit(Circuit):
    def fn(I):
        return I
    function_test_vectors = generate_function_test_vectors(Circuit, fn)
    simulator_test_vectors = generate_simulator_test_vectors(Circuit)
    assert function_test_vectors == simulator_test_vectors
