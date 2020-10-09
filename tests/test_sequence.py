import pytest

import magma as m
from hwtypes import BitVector

from fault.sequence import InputSequence, OutputSequence, SequenceTester


class ALUCore(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              opcode=m.In(m.UInt[2]),
              c=m.Out(m.UInt[16]))
    io.c @= m.mux([io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b],
                  io.opcode)


def core_input_driver(tester, value):
    a, b, opcode = value
    tester.circuit.a = a
    tester.circuit.b = b
    tester.circuit.opcode = opcode


def shared_output_monitor(tester, value):
    tester.circuit.c.expect(value)


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


def tile_input_driver(tester, args):
    a, b, opcode = args
    tester.circuit.config_en = 1
    tester.circuit.config_data = opcode
    tester.step(2)
    # Make sure enable logic works
    tester.circuit.config_en = 0
    tester.circuit.config_data = BitVector.random(2)
    tester.circuit.a = a
    tester.circuit.b = b


@pytest.mark.parametrize('circuit, input_driver, output_monitor, clock', [
    (ALUCore, core_input_driver, shared_output_monitor, None),
    (ALUTile, tile_input_driver, shared_output_monitor, ALUTile.CLK),
])
def test_simple_alu_sequence(circuit, input_driver, output_monitor, clock):
    """
    Reuse the same input/output sequence for core and tile
    """
    inputs = InputSequence([(BitVector.random(16), BitVector.random(16),
                             BitVector.random(2))
                            for _ in range(5)])

    ops = [
        lambda x, y: x + y,
        lambda x, y: x - y,
        lambda x, y: x * y,
        lambda x, y: x // y
    ]
    outputs = OutputSequence([ops[int(opcode)](a, b) for a, b, opcode in
                              inputs])

    tester = SequenceTester(circuit, [
        (input_driver, inputs),
        (output_monitor, outputs)
    ], clock=clock)

    tester.compile_and_run("verilator")
