import random
import common
from fault.magma_simulator_target import MagmaSimulatorTarget
from bit_vector import BitVector
import fault


def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize("backend", ["python", "coreir"])


def test_python_simulator_target_basic(backend):
    """
    Test basic python simuilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1)],
        [BitVector(1, 1), BitVector(0, 1)],
        [BitVector(0, 1), BitVector(1, 1)],
        [BitVector(0, 1), BitVector(0, 1)]
    ]
    target = MagmaSimulatorTarget(circ, test_vectors, None, backend=backend)
    target.run()


def test_python_simulator_target_nested_arrays(backend):
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    for i, val in enumerate(expected):
        tester.poke(circ.I[i], val)
    tester.eval()
    for i, val in enumerate(expected):
        tester.expect(circ.O[i], val)

    target = MagmaSimulatorTarget(circ, tester.test_vectors, None,
                                  backend=backend)
    target.run()


def test_python_simulator_target_clock(backend):
    circ = common.TestBasicClkCircuit
    test_vectors = [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)],
        [BitVector(0, 1), BitVector(0, 1), BitVector(1, 1)]
    ]
    target = MagmaSimulatorTarget(circ, test_vectors, circ.CLK,
                                  backend=backend)
    target.run()
