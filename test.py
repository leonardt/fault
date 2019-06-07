import magma as m
import mantle


class ConfigReg(m.Circuit):
    IO = ["D", m.In(m.Bits(2)), "Q", m.Out(m.Bits(2))] + \
        m.ClockInterface(has_ce=True)

    @classmethod
    def definition(io):
        reg = mantle.Register(2, has_ce=True, name="conf_reg")
        io.Q <= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    IO = ["a", m.In(m.UInt(16)),
          "b", m.In(m.UInt(16)),
          "c", m.Out(m.UInt(16)),
          "config_data", m.In(m.Bits(2)),
          "config_en", m.In(m.Enable),
          ] + m.ClockInterface()

    @classmethod
    def definition(io):
        opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
        io.c <= mantle.mux(
            [io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b], opcode)

import operator
import fault

ops = [operator.add, operator.sub, operator.mul, operator.floordiv]
tester = fault.Tester(SimpleALU, SimpleALU.CLK)
tester.circuit.CLK = 0
tester.circuit.config_en = 1
for i in range(0, 4):
    tester.circuit.config_data = i
    tester.step(2)
    tester.circuit.a = 3
    tester.circuit.b = 2
    tester.eval()
    tester.circuit.c.expect(ops[i](3, 2))

tester.compile_and_run("verilator", flags=["-Wno-fatal"], 
                       magma_opts={"verilator_debug": True}, directory="build")
tester.compile_and_run("system-verilog", simulator="ncsim", directory="build")
tester.compile_and_run("system-verilog", simulator="vcs", directory="build")
