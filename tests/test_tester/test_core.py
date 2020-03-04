import magma as m
import random
from hwtypes import BitVector
import hwtypes
import fault
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
import fault.actions as actions
import tempfile
import pytest
from pathlib import Path
from ..common import (pytest_sim_params, TestBasicCircuit, TestPeekCircuit,
                      TestBasicClkCircuit, TestNestedArraysCircuit,
                      TestBasicClkCircuitCopy, TestDoubleNestedArraysCircuit,
                      TestByteCircuit, TestArrayCircuit, TestUInt32Circuit,
                      TestSIntCircuit, TestTupleCircuit, TestNestedTupleCircuit,
                      TestUInt64Circuit, TestUInt128Circuit,
                      TestNestedArrayTupleCircuit)


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


def check(got, expected):
    assert type(got) == type(expected)
    if isinstance(got, actions.PortAction):
        assert got.port is expected.port
        assert got.value == expected.value
    elif isinstance(got, Print):
        assert got.format_str == expected.format_str
        assert all(p0 is p1 for p0, p1 in zip(got.ports, expected.ports))
    elif isinstance(got, Step):
        assert got.clock == expected.clock
        assert got.steps == expected.steps
    elif isinstance(got, Eval):
        pass
    else:
        raise NotImplementedError(type(got))


def test_tester_basic(target, simulator):
    circ = TestBasicCircuit
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
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    tester.poke(circ.I, True)
    tester.eval()
    tester.expect(circ.O, True)
    tester.poke(circ.I, False)
    tester.eval()
    tester.expect(circ.O, False)
    tester.poke(circ.I, False)
    tester.eval()
    tester.expect(circ.O, False)
    tester.poke(circ.I, hwtypes.Bit(1))
    tester.eval()
    tester.expect(circ.O, hwtypes.Bit(1))
    tester.poke(circ.I, hwtypes.Bit(0))
    tester.eval()
    tester.expect(circ.O, hwtypes.Bit(0))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)
    tester.compile_and_run("coreir")
    tester.clear()
    assert tester.actions == []


@pytest.mark.xfail(strict=True)
def test_tester_basic_fail(target, simulator):
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 0)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_clock(target, simulator):
    circ = TestPeekCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, 0)
    tester.expect(circ.O0, tester.peek(circ.O1))
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[1], Expect(circ.O0, Peek(circ.O1)))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_peek(target, simulator):
    circ = TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    check(tester.actions[0], Poke(circ.I, 0))
    check(tester.actions[2], Expect(circ.O, 0))
    tester.poke(circ.CLK, 0)
    check(tester.actions[3], Poke(circ.CLK, 0))
    tester.step()
    check(tester.actions[4], Step(circ.CLK, 1))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_no_clock_init():
    circ = TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    with pytest.warns(DeprecationWarning,
                      match="Clock has not been initialized, the initial "
                            "value will be X for system verilog targets.  In "
                            "a future release, this will be an error"):
        tester.step()
    # should not warn more than once
    with pytest.warns(None) as record:
        tester.step()
        assert len(record) == 0


def test_tester_peek_input(target, simulator):
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, tester.peek(circ.I))
    check(tester.actions[0], Poke(circ.I, 1))
    check(tester.actions[1], Eval())
    check(tester.actions[2], Expect(circ.O, Peek(circ.I)))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_nested_arrays_by_element(target, simulator):
    circ = TestNestedArraysCircuit
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
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_nested_arrays_bulk(target, simulator):
    circ = TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
    tester.poke(circ.I, val)
    tester.eval()
    tester.expect(circ.O, val)
    for i in range(3):
        expected.append(Poke(circ.I[i], val[i]))
    expected.append(Eval())
    for i in range(3):
        expected.append(Expect(circ.O[i], val[i]))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_double_nested_arrays_broadcast(target, simulator):
    circ = TestDoubleNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = []
    val = random.randint(0, (1 << 4) - 1)
    tester.poke(circ.I, val)
    for j in range(2):
        for i in range(3):
            expected.append(Poke(circ.I[j][i], val))
    tester.eval()
    expected.append(Eval())
    for j in range(2):
        for i in range(3):
            tester.expect(circ.O[j][i], val)
            expected.append(Expect(circ.O[j][i], val))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_nested_array_tuple_broadcast(target, simulator):
    circ = TestNestedArrayTupleCircuit
    tester = fault.Tester(circ)
    expected = []
    val = (random.randint(0, (1 << 4) - 1), random.randint(0, (1 << 4) - 1))
    tester.poke(circ.I, val)
    for j in range(2):
        for i in range(3):
            expected.append(Poke(circ.I[j][i].a, val[0]))
            expected.append(Poke(circ.I[j][i].b, val[1]))
    tester.eval()
    expected.append(Eval())
    for j in range(2):
        for i in range(3):
            tester.expect(circ.O[j][i], val)
            expected.append(Expect(circ.O[j][i].a, val[0]))
            expected.append(Expect(circ.O[j][i].b, val[1]))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_big_int(target, simulator):
    circ = TestUInt64Circuit
    tester = fault.Tester(circ)
    expected = []
    val = random.randint(0, (1 << 64) - 1)
    tester.poke(circ.I, val)
    tester.eval()
    tester.expect(circ.O, val)
    expected.append(Poke(circ.I, val))
    expected.append(Eval())
    expected.append(Expect(circ.O, val))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_128(target, simulator):
    circ = TestUInt128Circuit
    tester = fault.Tester(circ)
    expected = []
    val = random.randint(0, (1 << 128) - 1)
    tester.poke(circ.I, val)
    tester.eval()
    tester.expect(circ.O, val)
    expected.append(Poke(circ.I, val))
    expected.append(Eval())
    expected.append(Expect(circ.O, val))
    for i, exp in enumerate(expected):
        check(tester.actions[i], exp)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_retarget_tester(target, simulator):
    circ = TestBasicClkCircuit
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

    circ_copy = TestBasicClkCircuitCopy
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
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            copy.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            copy.compile_and_run(target, directory=_dir, simulator=simulator)


def test_run_error():
    try:
        circ = TestBasicCircuit
        fault.Tester(circ).run("bad_target")
        assert False, "Should raise an exception"
    except Exception as e:
        assert str(e) == f"Could not find target=bad_target, did you compile it first?"  # noqa


def test_print_tester(capsys):
    circ = TestBasicClkCircuit
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
    0: Poke(BasicClkCircuit.I, Bit(False))
    1: Eval()
    2: Expect(BasicClkCircuit.O, Bit(False))
    3: Poke(BasicClkCircuit.CLK, Bit(False))
    4: Step(BasicClkCircuit.CLK, steps=1)
    5: Print("%08x", BasicClkCircuit.O)
"""


def test_print_arrays(capsys):
    circ = TestDoubleNestedArraysCircuit
    tester = fault.Tester(circ)
    tester.poke(circ.I, [[0, 1, 2], [3, 4, 5]])
    tester.eval()
    tester.expect(circ.O, [[0, 1, 2], [3, 4, 5]])
    tester.print("%08x", circ.O)
    print(tester)
    out, err = capsys.readouterr()
    assert "\n".join(out.splitlines()[1:]) == """\
Actions:
    0: Poke(DoubleNestedArraysCircuit.I[0][0], 0)
    1: Poke(DoubleNestedArraysCircuit.I[0][1], 1)
    2: Poke(DoubleNestedArraysCircuit.I[0][2], 2)
    3: Poke(DoubleNestedArraysCircuit.I[1][0], 3)
    4: Poke(DoubleNestedArraysCircuit.I[1][1], 4)
    5: Poke(DoubleNestedArraysCircuit.I[1][2], 5)
    6: Eval()
    7: Expect(DoubleNestedArraysCircuit.O[0][0], 0)
    8: Expect(DoubleNestedArraysCircuit.O[0][1], 1)
    9: Expect(DoubleNestedArraysCircuit.O[0][2], 2)
    10: Expect(DoubleNestedArraysCircuit.O[1][0], 3)
    11: Expect(DoubleNestedArraysCircuit.O[1][1], 4)
    12: Expect(DoubleNestedArraysCircuit.O[1][2], 5)
    13: Print("%08x", DoubleNestedArraysCircuit.O)
"""  # nopep8


def test_tester_verilog_wrapped(target, simulator):
    ConfigReg, SimpleALU = m.DefineFromVerilogFile(
        "tests/simple_alu.v", type_map={"CLK": m.In(m.Clock)},
        target_modules=["SimpleALU", "ConfigReg"])
    SimpleALU.place(ConfigReg())

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
    tester.circuit.CLK = 0
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
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_loop(target, simulator):
    circ = TestArrayCircuit
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
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_file_io(target, simulator):
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        # determine absolute paths to file I/O locations
        test_file_in = (Path(_dir) / 'test_file_in.raw').resolve()
        test_file_out = (Path(_dir) / 'test_file_out.raw').resolve()
        if test_file_out.exists():
            test_file_out.unlink()

        # create testbench
        circ = TestByteCircuit
        tester = fault.Tester(circ)
        tester.zero_inputs()
        file_in = tester.file_open(str(test_file_in), "r")
        file_out = tester.file_open(str(test_file_out), "w")
        loop = tester.loop(8)
        value = loop.file_read(file_in)
        loop.poke(circ.I, value)
        loop.eval()
        loop.expect(circ.O, loop.index)
        loop.expect(circ.O, value)
        loop.file_write(file_out, circ.O)
        tester.file_close(file_in)
        tester.file_close(file_out)

        # write input
        with open(test_file_in, "wb") as file:
            file.write(bytes([i for i in range(8)]))

        # run simulation
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir,
                                   flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)

        # read output
        with open(test_file_out, "rb") as file:
            expected = bytes([i for i in range(8)])
            assert file.read(8) == expected


def test_tester_file_io_chunk_size_4_big_endian(target, simulator):
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        # determine absolute paths to file I/O locations
        test_file_in = (Path(_dir) / 'test_file_in.raw').resolve()
        test_file_out = (Path(_dir) / 'test_file_out.raw').resolve()
        if test_file_out.exists():
            test_file_out.unlink()

        # create testbench
        circ = TestUInt32Circuit
        tester = fault.Tester(circ)
        tester.zero_inputs()
        file_in = tester.file_open(str(test_file_in), "r", chunk_size=4,
                                   endianness="big")
        file_out = tester.file_open(str(test_file_out), "w", chunk_size=4,
                                    endianness="big")
        loop = tester.loop(8)
        value = loop.file_read(file_in)
        loop.poke(circ.I, value)
        loop.eval()
        loop.expect(circ.O, loop.index)
        loop.file_write(file_out, circ.O)
        tester.file_close(file_in)
        tester.file_close(file_out)

        # write input
        with open(test_file_in, "wb") as file:
            for i in range(8):
                file.write(bytes([0, 0, 0, i]))

        # run simulation
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)

        # read output
        with open(test_file_out, "rb") as file:
            for i in range(8):
                assert file.read(4) == bytes([0, 0, 0, i])


def test_tester_file_io_chunk_size_4_little_endian(target, simulator):
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        # determine absolute paths to file I/O locations
        test_file_in = (Path(_dir) / 'test_file_in.raw').resolve()
        test_file_out = (Path(_dir) / 'test_file_out.raw').resolve()
        if test_file_out.exists():
            test_file_out.unlink()

        # create testbench
        circ = TestUInt32Circuit
        tester = fault.Tester(circ)
        tester.zero_inputs()
        file_in = tester.file_open(str(test_file_in), "r", chunk_size=4)
        file_out = tester.file_open(str(test_file_out), "w", chunk_size=4)
        loop = tester.loop(8)
        value = loop.file_read(file_in)
        loop.poke(circ.I, value)
        loop.eval()
        loop.expect(circ.O, loop.index)
        loop.file_write(file_out, circ.O)
        tester.file_close(file_in)
        tester.file_close(file_out)

        # write input
        with open(test_file_in, "wb") as file:
            for i in range(8):
                file.write(bytes([i, 0, 0, 0]))

        # run simulation
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)

        # read output
        with open(test_file_out, "rb") as file:
            for i in range(8):
                assert file.read(4) == bytes([i, 0, 0, 0])


def test_tester_while(target, simulator):
    circ = TestArrayCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 0)
    tester.eval()
    loop = tester._while(tester.circuit.O != 1)
    loop.poke(circ.I, 1)
    loop.eval()
    tester.expect(circ.O, 1)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_while2(target, simulator):
    circ = TestArrayCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    loop = tester._while(tester.circuit.O == 0)
    loop.poke(circ.I, 1)
    loop.eval()
    tester.expect(circ.O, 1)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_while3(target, simulator):
    circ = TestArrayCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    loop = tester._while(tester.peek(tester._circuit.O) == 0)
    loop.poke(circ.I, 1)
    loop.eval()
    tester.expect(circ.O, 1)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_if(target, simulator):
    circ = TestArrayCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 0)
    loop = tester._while(tester.circuit.O != 1)
    loop._if(tester.circuit.O == 0).poke(circ.I, 1)
    loop.eval()
    if_tester = tester._if(tester.circuit.O == 0)
    if_tester.poke(circ.I, 1)
    if_tester._else().poke(circ.I, 0)
    tester.eval()
    tester.expect(circ.O, 0)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_tester_file_scanf(target, simulator):
    if simulator == "iverilog":
        pytest.skip("iverilog does not support scanf")

    with tempfile.TemporaryDirectory(dir=".") as _dir:
        # determine absolute paths to file I/O locations
        test_file_in = (Path(_dir) / 'test_file_in.txt').resolve()

        # create testbench
        circ = TestUInt32Circuit
        tester = fault.Tester(circ)
        tester.zero_inputs()
        file_in = tester.file_open(str(test_file_in), "r")
        config_addr = tester.Var("config_addr", BitVector[32])
        config_data = tester.Var("config_data", BitVector[32])
        loop = tester.loop(8)
        loop.file_scanf(file_in, "%x %x", config_addr, config_data)
        loop.poke(circ.I, config_addr + 1)
        loop.eval()
        loop.expect(circ.O, config_addr + 1)
        loop.poke(circ.I, config_data)
        loop.eval()
        loop.expect(circ.O, config_data)
        tester.file_close(file_in)

        # write input
        with open(test_file_in, "w") as file:
            file.write(hex(int(BitVector.random(32)))[2:])

        # run simulation
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)


def test_sint_circuit(target, simulator):
    circ = TestSIntCircuit
    tester = fault.Tester(circ)

    inputs = [hwtypes.SIntVector.random(4) for _ in range(10)]

    # have at least a few negative tests
    while sum(bool(x < 0) for x in inputs) < 3:
        inputs = [hwtypes.SIntVector.random(4) for _ in range(10)]

    for i in range(10):
        tester.circuit.I = int(inputs[i])
        tester.eval()
        tester.circuit.O.expect(inputs[i])
    for i in range(10):
        tester.circuit.I = inputs[i]
        tester.eval()
        tester.circuit.O.expect(int(inputs[i]))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


def test_tuple_circuit(target, simulator):
    circ = TestTupleCircuit

    tester = fault.Tester(circ)
    tester.circuit.I = (4, 2)
    tester.eval()
    tester.circuit.O.expect((4, 2))
    tester.circuit.I = {"a": 4, "b": 2}
    tester.eval()
    tester.circuit.O.expect({"a": 4, "b": 2})

    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


def test_nested_tuple_circuit(target, simulator):
    circ = TestNestedTupleCircuit

    tester = fault.Tester(circ)
    tester.circuit.I = ((4, 2), 2)
    tester.eval()
    tester.circuit.O.expect(((4, 2), 2))
    tester.circuit.I.a = (3, 1)
    tester.eval()
    tester.circuit.O.a.expect((3, 1))
    tester.circuit.O.expect(((3, 1), 2))
    tester.circuit.I = {"a": {"k": 4, "v": 2}, "b": 2}
    tester.eval()
    tester.circuit.O.expect({"a": {"k": 4, "v": 2}, "b": 2})
    tester.circuit.I = {"a": (6, 5), "b": 3}
    tester.eval()
    tester.circuit.O.expect({"a": (6, 5), "b": 3})
    tester.circuit.I = ({"k": 4, "v": 2}, 2)
    tester.eval()
    tester.circuit.O.expect(({"k": 4, "v": 2}, 2))

    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


def test_poke_bitwise(target, simulator):
    circ = TestArrayCircuit
    tester = fault.Tester(circ)
    tester.circuit.I = 0
    tester.eval()
    tester.circuit.I[0] = 1
    tester.circuit.I[2] = 1
    tester.eval()
    tester.circuit.O[0].expect(1)
    tester.circuit.O[1].expect(0)
    tester.circuit.O[2].expect(1)
    tester.circuit.I[1:] = 0b01
    tester.eval()
    tester.circuit.O[1:].expect(0b01)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


def test_poke_bitwise_nested(target, simulator):
    circ = TestNestedArraysCircuit
    tester = fault.Tester(circ)
    tester.circuit.I = 0
    tester.eval()
    tester.circuit.I[0][0] = 1
    tester.circuit.I[1][1] = 1
    tester.eval()
    tester.circuit.O[0][0].expect(1)
    tester.circuit.O[0][1].expect(0)
    tester.circuit.O[1][0].expect(0)
    tester.circuit.O[1][1].expect(1)
    tester.assert_((tester.circuit.O[0] | tester.circuit.O[1]) == 0b11)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        _dir = "build"
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


@pytest.mark.xfail(strict=True)
def test_generic_expect_fail(target, simulator):
    circ = TestNestedArraysCircuit
    tester = fault.Tester(circ)
    tester.circuit.I = 0
    tester.eval()
    tester.circuit.I[0][0] = 1
    tester.circuit.I[1][1] = 1
    tester.eval()
    tester.assert_((tester.circuit.O[0] | tester.circuit.O[1]) == 0b01)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {"target": target, "directory": _dir}
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)
