import magma as m
import random
from hwtypes import BitVector
import fault
from fault.actions import Poke, Expect, Eval, Step, Print, Peek, Loop
import common
import tempfile
import os
import shutil
import pytest


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if shutil.which("irun"):
            targets.append(
                ("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(
                ("system-verilog", "vcs"))
        if shutil.which("iverilog"):
            targets.append(
                ("system-verilog", "iverilog"))
        metafunc.parametrize("target,simulator", targets)


def check(got, expected):
    assert type(got) == type(expected)
    assert got.__dict__ == expected.__dict__


def test_tester_basic(target, simulator):
    circ = common.TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    check(tester.actions[0], Poke(circ.I, 0))
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 1)
    tester.print("%08x", circ.O)
    check(tester.actions[1], Poke(circ.I, 1))
    check(tester.actions[2], Eval())
    check(tester.actions[3], Expect(circ.O, 1))
    print(tester.actions[4])
    print(Print("%08x", circ.O))
    check(tester.actions[4], Print("%08x", circ.O))
    tester.eval()
    check(tester.actions[5], Eval())
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)
    tester.compile_and_run("coreir")
    tester.clear()
    assert tester.actions == []


@pytest.mark.xfail(strict=True)
def test_tester_basic_fail(target, simulator):
    circ = common.TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 0)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_clock(target, simulator):
    circ = common.TestPeekCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, 0)
    tester.expect(circ.O0, tester.peek(circ.O1))
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[1], Expect(circ.O0, Peek(circ.O1)))
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_peek(target, simulator):
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
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_nested_arrays_by_element(target, simulator):
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.poke(circ.I[i], val)
        tester.eval()
        tester.expect(circ.O[i], val)
        expected.append(Poke(circ.I[i], val))
        expected.append(Eval())
        expected.append(Expect(circ.O[i], val))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_nested_arrays_bulk(target, simulator):
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
    tester.poke(circ.I, val)
    tester.eval()
    tester.expect(circ.O, val)
    expected.append(Poke(circ.I, fault.array.Array(val, 3)))
    expected.append(Eval())
    expected.append(Expect(circ.O, fault.array.Array(val, 3)))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_retarget_tester(target, simulator):
    circ = common.TestBasicClkCircuit
    expected = [
        Poke(circ.I, 0),
        Eval(),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Step(circ.CLK, 1),
        Print("%08x", circ.O)
    ]
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    tester.poke(circ.CLK, 0)
    tester.step()
    tester.print("%08x", circ.O)
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)

    circ_copy = common.TestBasicClkCircuitCopy
    copy = tester.retarget(circ_copy, circ_copy.CLK)
    copy_expected = [
        Poke(circ_copy.I, 0),
        Eval(),
        Expect(circ_copy.O, 0),
        Poke(circ_copy.CLK, 0),
        Step(circ_copy.CLK, 1),
        Print("%08x", circ_copy.O)
    ]
    for i, exp in enumerate(copy_expected):
        check(copy.actions[i], exp)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            copy.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            copy.compile_and_run(target, directory=_dir, simulator=simulator)


def test_run_error():
    try:
        circ = common.TestBasicCircuit
        fault.Tester(circ).run("bad_target")
        assert False, "Should raise an exception"
    except Exception as e:
        assert str(e) == f"Could not find target=bad_target, did you compile it first?"  # noqa


def test_print_tester(capsys):
    circ = common.TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    tester.poke(circ.CLK, 0)
    tester.step()
    tester.print("%08x", circ.O)
    print(tester)
    out, err = capsys.readouterr()
    assert "\n".join(out.splitlines()[1:]) == """\
Actions:
    0: Poke(BasicClkCircuit.I, 0)
    1: Eval()
    2: Expect(BasicClkCircuit.O, 0)
    3: Poke(BasicClkCircuit.CLK, 0)
    4: Step(BasicClkCircuit.CLK, steps=1)
    5: Print("%08x", BasicClkCircuit.O)
"""


def test_print_arrays(capsys):
    circ = common.TestDoubleNestedArraysCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, [[0, 1, 2], [3, 4, 5]])
    tester.eval()
    tester.expect(circ.O, [[0, 1, 2], [3, 4, 5]])
    tester.print("%08x", circ.O)
    print(tester)
    out, err = capsys.readouterr()
    assert "\n".join(out.splitlines()[1:]) == """\
Actions:
    0: Poke(DoubleNestedArraysCircuit.I, Array([Array([BitVector[4](0), BitVector[4](1), BitVector[4](2)], 3), Array([BitVector[4](3), BitVector[4](4), BitVector[4](5)], 3)], 2))
    1: Eval()
    2: Expect(DoubleNestedArraysCircuit.O, Array([Array([BitVector[4](0), BitVector[4](1), BitVector[4](2)], 3), Array([BitVector[4](3), BitVector[4](4), BitVector[4](5)], 3)], 2))
    3: Print("%08x", DoubleNestedArraysCircuit.O)
"""  # nopep8


def test_tester_verilog_wrapped(target, simulator):
    SimpleALU = m.DefineFromVerilogFile("tests/simple_alu.v",
                                        type_map={"CLK": m.In(m.Clock)},
                                        target_modules=["SimpleALU"])[0]

    circ = m.DefineCircuit("top",
                           "a", m.In(m.Bits[16]),
                           "b", m.In(m.Bits[16]),
                           "c", m.Out(m.Bits[16]),
                           "config_data", m.In(m.Bits[2]),
                           "config_en", m.In(m.Bit),
                           "CLK", m.In(m.Clock))
    simple_alu = SimpleALU()
    m.wire(simple_alu.a, circ.a)
    m.wire(simple_alu.b, circ.b)
    m.wire(simple_alu.c, circ.c)
    m.wire(simple_alu.config_data, circ.config_data)
    m.wire(simple_alu.config_en, circ.config_en)
    m.wire(simple_alu.CLK, circ.CLK)
    m.EndDefine()

    tester = fault.Tester(circ, circ.CLK)
    tester.verilator_include("SimpleALU")
    tester.verilator_include("ConfigReg")
    for i in range(0, 4):
        tester.poke(
            fault.WrappedVerilogInternalPort("SimpleALU_inst0.config_reg.Q",
                                             m.Bits[2]),
            i)
        tester.step(2)
        tester.expect(
            fault.WrappedVerilogInternalPort("SimpleALU_inst0.opcode",
                                             m.Bits[2]),
            i)
        signal = tester.peek(
            fault.WrappedVerilogInternalPort("SimpleALU_inst0.opcode",
                                             m.Bits[2]))
        tester.expect(
            fault.WrappedVerilogInternalPort("SimpleALU_inst0.opcode",
                                             m.Bits[2]),
            signal)
        tester.expect(
            fault.WrappedVerilogInternalPort(
                "SimpleALU_inst0.config_reg.Q", m.Bits[2]),
            i)
        signal = tester.peek(
            fault.WrappedVerilogInternalPort(
                "SimpleALU_inst0.config_reg.Q", m.Bits[2]))
        tester.expect(
            fault.WrappedVerilogInternalPort(
                "SimpleALU_inst0.config_reg.Q", m.Bits[2]),
            signal)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_loop(target, simulator):
    circ = common.TestArrayCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    loop = tester.loop(7)
    loop.poke(circ.I, loop.index)
    loop.eval()
    loop.expect(circ.O, loop.index)
    assert tester.actions[1].n_iter == 7
    for actual, expected in zip(tester.actions[1].actions,
                                [Poke(circ.I, loop.index),
                                 Eval(),
                                 Expect(circ.O, loop.index)]):
        check(actual, expected)
    with tempfile.TemporaryDirectory() as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_file_io(target, simulator):
    circ = common.TestByteCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    file_in = tester.file_open("test_file_in.raw", "r")
    out_file = "test_file_out.raw"
    file_out = tester.file_open(out_file, "w")
    loop = tester.loop(8)
    value = loop.file_read(file_in)
    loop.poke(circ.I, value)
    loop.eval()
    loop.expect(circ.O, loop.index)
    loop.file_write(file_out, circ.O)
    tester.file_close(file_in)
    tester.file_close(file_out)
    with tempfile.TemporaryDirectory() as _dir:
        if os.path.exists(_dir + "/" + out_file):
            os.remove(_dir + "/" + out_file)
        with open(_dir + "/test_file_in.raw", "wb") as file:
            file.write(bytes([i for i in range(8)]))
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)
        with open(_dir + "/test_file_out.raw", "rb") as file:
            expected = bytes([i for i in range(8)])
            if simulator == "iverilog":
                # iverilog doesn't support writing a NULL byte out using %c, so
                # this first value is skipped
                expected = expected[1:]
            assert file.read(8) == expected
