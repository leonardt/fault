import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random


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


def test_tester_nested_arrays():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.poke(circ.I[i], val)
        tester.expect(circ.O[i], val)

    with tempfile.TemporaryDirectory() as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")

        target = fault.verilator_target.VerilatorTarget(
            circ, tester.test_vectors, directory=f"{tempdir}/")
        target.run()
