from bit_vector import BitVector
import common
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.random import random_bv


# NOTE(rsetaluri): The python simulator backend is not tested since it is not
# being actively supported currently. If it is updated, we should add it the
# test fixtures.
def pytest_generate_tests(metafunc):
    if 'backend' in metafunc.fixturenames:
        metafunc.parametrize("backend", ["coreir"])


def run(circ, actions, clock, backend):
    target = MagmaSimulatorTarget(circ, clock, backend=backend)
    target.run(actions)


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


def test_magma_simulator_target_nested_arrays_by_element(backend):
    circ = common.TestNestedArraysCircuit
    expected = [random_bv(4) for i in range(3)]
    actions = []
    for i, val in enumerate(expected):
        actions.append(Poke(circ.I[i], val))
    actions.append(Eval())
    for i, val in enumerate(expected):
        actions.append(Expect(circ.O[i], val))
    run(circ, actions, None, backend)


def test_magma_simulator_target_nested_arrays_bulk(backend):
    circ = common.TestNestedArraysCircuit
    expected = [random_bv(4) for i in range(3)]
    actions = []
    actions.append(Poke(circ.I, expected))
    actions.append(Eval())
    actions.append(Expect(circ.O, expected))
    run(circ, actions, None, backend)


def test_magma_simulator_target_clock(backend, capfd):
    circ = common.TestBasicClkCircuit
    actions = [
        Poke(circ.I, BitVector(0, 1)),
        Print(circ.I),
        Expect(circ.O, BitVector(0, 1)),
        # TODO(rsetaluri): Figure out how to set clock value directly with the
        # coreir simulator. Currently it does not allow this.
        # Poke(circ.CLK, BitVector(0, 1)),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector(1, 1)),
        Eval(),
        Print(circ.O),
    ]
    run(circ, actions, circ.CLK, backend)
    out, err = capfd.readouterr()
    lines = out.splitlines()

    assert lines[-2] == "BasicClkCircuit.I = 0", "Print output incorrect"
    assert lines[-1] == "BasicClkCircuit.O = 1", "Print output incorrect"


def test_magma_simulator_target_peek(backend):
    circ = common.TestPeekCircuit
    actions = []
    for i in range(3):
        x = random_bv(3)
        actions.append(Poke(circ.I, x))
        actions.append(Eval())
        actions.append(Expect(circ.O0, Peek(circ.O1)))
    run(circ, actions, None, backend)


if __name__ == "__main__":
    test_magma_simulator_target_basic("coreir")
