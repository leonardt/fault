from hwtypes import BitVector
import magma as m
import fault as f
from fault.verilator_utils import verilator_version
import pytest


class Main(m.Circuit):
    io = m.IO(I=m.Consumer(m.ReadyValid[m.UInt[8]]),
              O=m.Producer(m.ReadyValid[m.UInt[8]])) + m.ClockIO()
    count = m.Register(m.UInt[2])()
    count.I @= count.O + 1
    enable = io.I.valid & (count.O == 3) & io.O.ready
    io.I.ready @= enable
    io.O.data @= m.Register(m.UInt[8], has_enable=True)()(io.I.data + 1,
                                                          CE=enable)
    io.O.valid @= enable


def test_basic_ready_valid_sequence():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    I = [BitVector.random(8) for _ in range(8)] + [0]
    O = [0] + [i + 1 for i in I[:-1]]
    f.run_ready_valid_test(Main, {"I": I, "O": O}, "verilator")


def test_basic_ready_valid_sequence_fail():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    I = [BitVector.random(8) for _ in range(8)] + [0]
    O = [0] + [i - 1 for i in I[:-1]]
    with pytest.raises(AssertionError):
        f.run_ready_valid_test(Main, {"I": I, "O": O}, "verilator")


class Main2(m.Circuit):
    io = m.IO(I=m.Consumer(m.ReadyValid[m.UInt[8]]),
              O=m.Producer(m.ReadyValid[m.UInt[8]]),
              inc=m.In(m.UInt[8]),
              ) + m.ClockIO()
    count = m.Register(m.UInt[2])()
    count.I @= count.O + 1
    enable = io.I.valid & (count.O == 3) & io.O.ready
    io.I.ready @= enable
    io.O.data @= m.Register(m.UInt[8], has_enable=True)()(io.I.data + io.inc,
                                                          CE=enable)
    io.O.valid @= enable


def test_lifted_ready_valid_sequence_simple():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    I = [BitVector.random(8) for _ in range(8)] + [0]
    O = [0] + [i + 2 for i in I[:-1]]
    tester = f.ReadyValidTester(Main2, {"I": I, "O": O})
    tester.circuit.inc = 2
    tester.finish_sequences()
    tester.compile_and_run("verilator", disp_type="realtime",
                           flags=['-Wno-UNUSED'])


def test_lifted_ready_valid_sequence_simple_fail():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    I = [BitVector.random(8) for _ in range(8)] + [0]
    O = [0] + [i + 2 for i in I[:-1]]
    tester = f.ReadyValidTester(Main2, {"I": I, "O": O})
    tester.circuit.inc = 2
    # Should work for a few cycles
    for i in range(9):
        tester.advance_cycle()
    # Bad inc should fail
    tester.circuit.inc = 3
    tester.finish_sequences()
    with pytest.raises(AssertionError):
        tester.compile_and_run("verilator", disp_type="realtime")


def test_lifted_ready_valid_sequence_changing_inc():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    I = [BitVector.random(8) for _ in range(8)] + [0]
    O = [0] + [I[i] + ((i + 1) % 2) for i in range(8)]
    tester = f.ReadyValidTester(Main2, {"I": I, "O": O})
    # Sequence expects inc to change over time
    for i in range(8):
        tester.circuit.inc = i % 2
        tester.advance_cycle()
        tester.wait_until_high(tester.circuit.O.ready & tester.circuit.O.valid)
    # Advance one cycle to finish last handshake
    tester.advance_cycle()
    tester.expect_sequences_finished()
    tester.compile_and_run("verilator", disp_type="realtime",
                           flags=['-Wno-UNUSED'])
