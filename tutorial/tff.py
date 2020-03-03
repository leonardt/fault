import magma as m
import mantle
import fault


class TFF(m.Circuit):
    io = m.IO(O=m.Out(m.Bit), CLK=m.In(m.Clock))

    reg = mantle.Register(None, name="tff_reg")
    reg.CLK <= io.CLK
    reg.I <= ~reg.O
    io.O <= reg.O


tff_tester = fault.Tester(TFF, clock=TFF.CLK)
for i in range(8):
    tff_tester.circuit.O.expect(i % 2)
    tff_tester.step(2)
tff_tester.compile_and_run("verilator")
