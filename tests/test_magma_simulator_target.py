import random
import common
from fault.magma_simulator_target import MagmaSimulatorTarget
from bit_vector import BitVector
import fault


def test_python_simulator_target_basic():
    """
    Test basic python simuilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1)],
        [BitVector(1, 1), BitVector(1, 1)]
    ]
    target = MagmaSimulatorTarget(circ, test_vectors, None)
    target.run()


def test_python_simulator_target_nested_arrays():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    for i, val in enumerate(expected):
        tester.poke(circ.I[i], val)
    tester.eval()
    for i, val in enumerate(expected):
        tester.expect(circ.O[i], val)

    target = MagmaSimulatorTarget(circ, tester.test_vectors, None)
    target.run()


def test_python_simulator_target_clock():
    circ = common.TestBasicClkCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)],
        [BitVector(0, 1), BitVector(0, 1), BitVector(1, 1)]
    ]
    target = MagmaSimulatorTarget(circ, test_vectors, circ.CLK)
    target.run()
