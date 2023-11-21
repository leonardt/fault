import tempfile

import hwtypes as ht
import fault as f
import magma as m


def test_fault_no_coreir():
    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.Bits[16]), O=m.Out(m.Bits[16]))
        io.O @= io.I & 0xFF

    tester = f.Tester(Foo)
    tester.circuit.I = I = ht.BitVector.random(16)
    tester.eval()
    tester.circuit.O.expect(I & 0xFF)

    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        tester.compile_and_run("verilator", magma_output="mlir-verilog",
                               directory=tempdir)
