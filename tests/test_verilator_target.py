import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random


def test_verilator_target_basic():
    """
    Test basic verilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    with tempfile.TemporaryDirectory() as tempdir:
        # Compile to verilog.
        # TODO(rsetaluri): Make this part of the target itself.
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")

        test_vectors = [[BitVector(0, 1), BitVector(0, 1)]]
        target = fault.verilator_target.VerilatorTarget(
            circ, test_vectors, directory=f"{tempdir}/")
        target.run()


def test_tester_nested_arrays():
    circ = common.TestNestedArraysCircuit
    tester = fault.Tester(circ)
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    for i, val in enumerate(expected):
        tester.poke(circ.I[i], val)
    tester.eval()
    for i, val in enumerate(expected):
        tester.expect(circ.O[i], val)

    with tempfile.TemporaryDirectory() as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")

        target = fault.verilator_target.VerilatorTarget(
            circ, tester.test_vectors, directory=f"{tempdir}/")
        target.run()
