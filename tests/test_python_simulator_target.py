import random
import magma as m
import common
from fault.python_simulator_target import *
from bit_vector import BitVector


def test_python_simulator_target_basic():
    """
    Test basic python simuilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1)],
        [BitVector(1, 1), BitVector(1, 1)]
    ]
    target = PythonSimulatorTarget(circ, test_vectors, None)
    target.run()


def test_python_simulator_target_nested_arrays():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.poke(circ.I[i], val)
        tester.expect(circ.O[i], val)

    target = PythonSimulatorTarget(circ, tester.test_vectors, None)
    target.run()


def test_python_simulator_target_clock():
    circ = common.TestBasicClkCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)],
        [BitVector(0, 1), BitVector(0, 1), BitVector(1, 1)]
    ]
    target = PythonSimulatorTarget(circ, test_vectors, circ.CLK)
    target.run()
