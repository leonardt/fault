import magma as m
import fault as f


def test_sv_compile():
    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit))
        io.O @= io.I

    tester = f.Tester(Foo)
    tester.circuit.I = 1
    tester.eval()
    tester.circuit.O.expect(1)
    tester.compile_and_run("system-verilog", simulator="iverilog",
            magma_opts={"sv": True})
