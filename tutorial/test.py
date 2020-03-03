import magma as m
import fault


class Passthrough(m.Circuit):
    io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))

    io.O <= io.I


passthrough_tester = fault.Tester(Passthrough)
passthrough_tester.circuit.I = 1
passthrough_tester.eval()
passthrough_tester.circuit.O.expect(1)
passthrough_tester.compile_and_run("verilator")
