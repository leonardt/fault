from fault.test_vectors import generate_function_test_vectors, \
    generate_simulator_test_vectors
from common import TestBasicCircuit


def test_test_vectors():
    def fn(I):
        return I
    function_test_vectors = generate_function_test_vectors(
        TestBasicCircuit, fn)
    simulator_test_vectors = generate_simulator_test_vectors(TestBasicCircuit)
    assert function_test_vectors == simulator_test_vectors
