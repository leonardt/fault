import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random
from fault.actions import Poke, Expect, Eval


def run(circ, actions):
    with tempfile.TemporaryDirectory() as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")
        target = fault.verilator_target.VerilatorTarget(
            circ, actions, directory=f"{tempdir}/", skip_compile=True)
        target.run()


def test_verilator_target_basic():
    """
    Test basic verilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    actions = (Poke(circ.I, 0), Eval(), Expect(circ.O, 0))
    run(circ, actions)


def test_verilator_target_nested_arrays():
    circ = common.TestNestedArraysCircuit
    expected = [random.randint(0, (1 << 4) - 1) for i in range(3)]
    actions = []
    for i, val in enumerate(expected):
        actions.append(Poke(circ.I[i], val))
    actions.append(Eval())
    for i, val in enumerate(expected):
        actions.append(Expect(circ.O[i], val))
    run(circ, actions)
