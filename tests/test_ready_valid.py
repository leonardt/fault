from hwtypes import BitVector
import magma as m
import fault as f


def test_basic_ready_valid_sequence():
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

    I = [BitVector.random(8) for _ in range(8)]
    O = [i + 1 for i in I]
    f.run_ready_valid_test(Main, {"I": I, "O": O}, "verilator")
