import random
from bit_vector import BitVector
import fault
from fault.actions import Poke, Expect, Eval, Step, Peek
import common


def check(got, expected):
    assert type(got) == type(expected)
    assert got.__dict__ == expected.__dict__


def test_tester_basic():
    circ = common.TestBasicCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    tester.peek(circ.O, "%08x")
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[1], Expect(circ.O, 0))
    check(tester.actions[2], Peek(circ.O, "%08x"))
    tester.eval()
    check(tester.actions[3], Eval())


def test_tester_clock():
    circ = common.TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[1], Expect(circ.O, 0))
    tester.poke(circ.CLK, 0)
    check(tester.actions[2], Poke(circ.CLK, 0))
    tester.step()
    check(tester.actions[3], Step(circ.CLK, 1))


def test_tester_nested_arrays():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.poke(circ.I[i], val)
        tester.expect(circ.O[i], val)
        expected.append(Poke(circ.I[i], val))
        expected.append(Expect(circ.O[i], val))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)


def test_copy_tester():
    circ = common.TestBasicClkCircuit
    expected = [
        Poke(circ.I, 0),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Step(circ.CLK, 1)
    ]
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    tester.poke(circ.CLK, 0)
    tester.step()
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)

    circ_copy = common.TestBasicClkCircuitCopy
    copy = tester.retarget(circ_copy, circ_copy.CLK)
    copy_expected = [
        Poke(circ_copy.I, 0),
        Expect(circ_copy.O, 0),
        Poke(circ_copy.CLK, 0),
        Step(circ_copy.CLK, 1)
    ]
    for i, exp in enumerate(copy_expected):
        check(copy.actions[i], exp)
