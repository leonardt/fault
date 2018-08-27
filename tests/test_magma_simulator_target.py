from bit_vector import BitVector
import common
from fault.actions import Poke, Expect, Eval, Step
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.random import random_bv


# NOTE(rsetaluri): The python simulator backend is not tested since it is not
# being actively supported currently. If it is updated, we should add it the
# test fixtures.
def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize("backend", ["coreir"])


def run(circ, actions, clock, backend):
    target = MagmaSimulatorTarget(circ, actions, clock, backend=backend)
    target.run()


def test_magma_simulator_target_basic(backend):
    """
    Test basic python simulator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    actions = [
        Poke(circ.I, BitVector(0, 1)),
        Expect(circ.O, BitVector(0, 1)),
        Eval(),
        Poke(circ.I, BitVector(1, 1)),
        Expect(circ.O, BitVector(0, 1)),
        Eval(),
        Poke(circ.I, BitVector(0, 1)),
        Expect(circ.O, BitVector(1, 1)),
        Eval(),
        Expect(circ.O, BitVector(0, 1)),
    ]
    run(circ, actions, None, backend)


def test_magma_simulator_target_nested_arrays(backend):
    circ = common.TestNestedArraysCircuit
    expected = [random_bv(4) for i in range(3)]
    actions = []
    for i, val in enumerate(expected):
        actions.append(Poke(circ.I[i], val))
    actions.append(Eval())
    for i, val in enumerate(expected):
        actions.append(Expect(circ.O[i], val))
    run(circ, actions, None, backend)


def test_magma_simulator_target_clock(backend):
    circ = common.TestBasicClkCircuit
    actions = [
        Poke(circ.I, BitVector(0, 1)),
        Expect(circ.O, BitVector(0, 1)),
        # TODO(rsetaluri): Figure out how to set clock value directly with the
        # coreir simulator. Currently it does not allow this.
        # Poke(circ.CLK, BitVector(0, 1)),
        Step(1, circ.CLK),
    ]
    run(circ, actions, circ.CLK, backend)
