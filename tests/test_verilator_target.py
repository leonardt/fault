import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random
from fault.actions import Poke, Expect, Eval, Step, Peek


def run(circ, actions, flags=[]):
    with tempfile.TemporaryDirectory() as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")
        target = fault.verilator_target.VerilatorTarget(
            circ, actions, directory=f"{tempdir}/",
            flags=flags, skip_compile=True)
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


def test_verilator_target_clock(capfd):
    circ = common.TestBasicClkCircuit
    actions = [
        Poke(circ.I, 0),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Peek(circ.O),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector(1, 1)),
        Eval(),
        Peek(circ.O),
    ]
    run(circ, actions, flags=["-Wno-lint"])
    out, err = capfd.readouterr()
    assert out.splitlines()[-1] == "BasicClkCircuit.O = 1", \
        "Peek output incorrect"
