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
    with pytest.raises(AssertionError) as e:
        f.run_ready_valid_test(Main, {"I": I, "O": O}, "verilator")
