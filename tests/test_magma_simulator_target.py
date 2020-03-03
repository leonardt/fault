from hwtypes import BitVector
from fault import Tester
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
from fault.magma_simulator_target import MagmaSimulatorTarget
from fault.random import random_bv
from .common import (TestBasicCircuit, TestNestedArraysCircuit,
                     TestBasicClkCircuit, TestPeekCircuit)


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
    circ = TestBasicCircuit
    actions = [
        Poke(circ.I, BitVector[1](0)),
        Expect(circ.O, BitVector[1](0)),
        Eval(),
        Poke(circ.I, BitVector[1](1)),
        Expect(circ.O, BitVector[1](0)),
        Eval(),
        Poke(circ.I, BitVector[1](0)),
        Expect(circ.O, BitVector[1](1)),
        Eval(),
        Expect(circ.O, BitVector[1](0)),
    ]
    run(circ, actions, None, backend)


def test_magma_simulator_target_nested_arrays_by_element(backend):
    circ = TestNestedArraysCircuit
    expected = [random_bv(4) for i in range(3)]
    actions = []
    for i, val in enumerate(expected):
        actions.append(Poke(circ.I[i], val))
    actions.append(Eval())
    for i, val in enumerate(expected):
        actions.append(Expect(circ.O[i], val))
    run(circ, actions, None, backend)


def test_magma_simulator_target_nested_arrays_bulk(backend):
    circ = TestNestedArraysCircuit
    expected = [random_bv(4) for i in range(3)]
    actions = []
    actions.append(Poke(circ.I, expected))
    actions.append(Eval())
    actions.append(Expect(circ.O, expected))
    run(circ, actions, None, backend)


def test_magma_simulator_target_clock(backend, capfd):
    circ = TestBasicClkCircuit
    actions = [
        Poke(circ.I, BitVector[1](0)),
        Print("%d\n", circ.I),
        Expect(circ.O, BitVector[1](0)),
        # TODO(rsetaluri): Figure out how to set clock value directly with the
        # coreir simulator. Currently it does not allow this.
        # Poke(circ.CLK, BitVector[1](0)),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector[1](1)),
        Eval(),
        Print("%d\n", circ.O),
    ]
    run(circ, actions, circ.CLK, backend)
    out, err = capfd.readouterr()
    lines = out.splitlines()
    print(lines)

    assert lines[-2] == "0", "Print output incorrect"
    assert lines[-1] == "1", "Print output incorrect"


def test_magma_simulator_target_peek(backend):
    circ = TestPeekCircuit
    actions = []
    for i in range(3):
        x = random_bv(3)
        actions.append(Poke(circ.I, x))
        actions.append(Eval())
        actions.append(Expect(circ.O0, Peek(circ.O1)))
    run(circ, actions, None, backend)


if __name__ == "__main__":
    test_magma_simulator_target_basic("coreir")
