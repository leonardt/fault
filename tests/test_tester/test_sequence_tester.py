import pytest

import magma as m
from hwtypes import BitVector

from fault.tester.sequence_tester import Monitor, Driver, SequenceTester


class ALUCore(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              opcode=m.In(m.UInt[2]),
              c=m.Out(m.UInt[16]))
    io.c @= m.mux([io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b],
                  io.opcode)


class ALUTile(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              config_data=m.In(m.UInt[2]),
              config_en=m.In(m.Enable),
              c=m.Out(m.UInt[16])) + m.ClockIO()
    config_reg = m.Register(m.Bits[2], has_enable=True)()
    config_reg.CE @= io.config_en
    config_reg.I @= io.config_data
    alu = ALUCore()
    io.c @= alu(io.a, io.b, config_reg.O)


class CoreDriver(Driver):
    def lower(self, a, b, opcode):
        self.tester.circuit.a = a
        self.tester.circuit.b = b
        self.tester.circuit.opcode = opcode


class TileDriver(Driver):
    def lower(self, a, b, opcode):
        self.tester.circuit.config_en = 1
        self.tester.circuit.config_data = opcode
        self.tester.step(2)
        # Make sure enable logic works
        self.tester.circuit.config_en = 0
        self.tester.circuit.config_data = BitVector.random(2)
        self.tester.circuit.a = a
        self.tester.circuit.b = b


class SharedMonitor(Monitor):
    def __init__(self):
        self.ops = [
            lambda x, y: x + y,
            lambda x, y: x - y,
            lambda x, y: x * y,
            lambda x, y: x // y
        ]

    def observe(self, a, b, opcode):
        expected = self.ops[int(opcode)](a, b)
        self.tester.circuit.c.expect(expected)


@pytest.mark.parametrize('circuit, driver, monitor, clock', [
    (ALUCore, CoreDriver(), SharedMonitor(), None),
    (ALUTile, TileDriver(), SharedMonitor(), ALUTile.CLK),
])
def test_simple_alu_sequence(circuit, driver, monitor, clock):
    """
    Reuse the same input/output sequence for core and tile
    """
    sequence = [
        (BitVector.random(16), BitVector.random(16), BitVector.random(2))
        for _ in range(5)
    ]

    tester = SequenceTester(circuit, driver, monitor, sequence, clock=clock)

    tester.compile_and_run("verilator")
