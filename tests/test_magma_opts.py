import tempfile
import magma as m
import fault as f


def test_verilog_prefix():
    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.Bits[4]), O=m.Out(m.Bits[4]))
        io.O @= io.I

    tester = f.Tester(Foo)
    tester.circuit.I = 4
    tester.eval()
    tester.circuit.O.expect(4)

    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        tester.compile_and_run("verilator",
                               magma_opts={"verilog_prefix": "bar_"},
                               directory=tempdir)
