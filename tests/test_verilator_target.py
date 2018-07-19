import tempfile
import magma as m
import fault
from bit_vector import BitVector


def test_verilator_target():
    """
    Test basic verilator workflow with a simple circuit.
    """

    class Foo(m.Circuit):
        IO = ["I", m.In(m.Bit), "O", m.Out(m.Bit)]

        @classmethod
        def definition(io):
            m.wire(io.I, io.O)

    with tempfile.TemporaryDirectory() as tempdir:
        # Compile to verilog.
        # TODO(rsetaluri): Make this part of the target itself.
        m.compile(f"{tempdir}/Foo", Foo, output="verilog")

        test_vectors = [[BitVector(0, 1), BitVector(0, 1)]]
        target = fault.verilator_target.VerilatorTarget(
            Foo, test_vectors, directory=f"{tempdir}/")
        target.run()
