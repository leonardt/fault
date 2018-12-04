import random
from bit_vector import BitVector
import fault
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
import common
import tempfile


def check(got, expected):
    assert type(got) == type(expected)
    assert got.__dict__ == expected.__dict__


def test_tester_basic():
    circ = common.TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    check(tester.actions[0], Poke(circ.I, 0))
    tester.poke(circ.I, 1)
    tester.expect(circ.O, 0)
    tester.print(circ.O, "%08x")
    check(tester.actions[1], Poke(circ.I, 1))
    check(tester.actions[2], Expect(circ.O, 0))
    check(tester.actions[3], Print(circ.O, "%08x"))
    tester.eval()
    check(tester.actions[4], Eval())
    with tempfile.TemporaryDirectory() as _dir:
        tester.compile_and_run("verilator", directory=_dir)
    tester.compile_and_run("coreir")
    tester.clear()
    assert tester.actions == []


def test_tester_clock():
    circ = common.TestPeekCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, 0)
    tester.expect(circ.O0, tester.peek(circ.O1))
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[1], Expect(circ.O0, Peek(circ.O1)))


def test_tester_peek():
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


def test_tester_nested_arrays_by_element():
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


def test_tester_nested_arrays_bulk():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
    tester.poke(circ.I, val)
    tester.expect(circ.O, val)
    expected.append(Poke(circ.I, fault.array.Array(val, 3)))
    expected.append(Expect(circ.O, fault.array.Array(val, 3)))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)


def test_retarget_tester():
    circ = common.TestBasicClkCircuit
    expected = [
        Poke(circ.I, 0),
        Eval(),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Step(circ.CLK, 1),
        Print(circ.O, "%08x")
    ]
    tester = fault.Tester(circ, circ.CLK, default_print_format_str="%08x")
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    tester.poke(circ.CLK, 0)
    tester.step()
    tester.print(circ.O)
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)

    circ_copy = common.TestBasicClkCircuitCopy
    copy = tester.retarget(circ_copy, circ_copy.CLK)
    assert copy.default_print_format_str == "%08x"
    copy_expected = [
        Poke(circ_copy.I, 0),
        Eval(),
        Expect(circ_copy.O, 0),
        Poke(circ_copy.CLK, 0),
        Step(circ_copy.CLK, 1),
        Print(circ_copy.O, "%08x")
    ]
    for i, exp in enumerate(copy_expected):
        check(copy.actions[i], exp)


def test_run_error():
    try:
        circ = common.TestBasicCircuit
        fault.Tester(circ).run("bad_target")
        assert False, "Should raise an exception"
    except Exception as e:
        assert str(e) == f"Could not find target=bad_target, did you compile it first?"  # noqa


def test_print_tester(capsys):
    circ = common.TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK, default_print_format_str="%08x")
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    tester.poke(circ.CLK, 0)
    tester.step()
    tester.print(circ.O)
    print(tester)
    out, err = capsys.readouterr()
    assert "\n".join(out.splitlines()[1:]) == """\
Actions:
    0: Poke(BasicClkCircuit.I, 0)
    1: Eval()
    2: Expect(BasicClkCircuit.O, 0)
    3: Poke(BasicClkCircuit.CLK, 0)
    4: Step(BasicClkCircuit.CLK, steps=1)
    5: Print(BasicClkCircuit.O, "%08x")
"""


def test_print_arrays(capsys):
    circ = common.TestDoubleNestedArraysCircuit
    tester = fault.Tester(circ, default_print_format_str="%08x")
    tester.poke(circ.I, [[0, 1, 2], [3, 4, 5]])
    tester.eval()
    tester.expect(circ.O, [[0, 1, 2], [3, 4, 5]])
    tester.print(circ.O)
    print(tester)
    out, err = capsys.readouterr()
    assert "\n".join(out.splitlines()[1:]) == """\
Actions:
    0: Poke(DoubleNestedArraysCircuit.I, Array([Array([BitVector(0, 4), BitVector(1, 4), BitVector(2, 4)], 3), Array([BitVector(3, 4), BitVector(4, 4), BitVector(5, 4)], 3)], 2))
    1: Eval()
    2: Expect(DoubleNestedArraysCircuit.O, Array([Array([BitVector(0, 4), BitVector(1, 4), BitVector(2, 4)], 3), Array([BitVector(3, 4), BitVector(4, 4), BitVector(5, 4)], 3)], 2))
    3: Print(DoubleNestedArraysCircuit.O, "%08x")
"""
