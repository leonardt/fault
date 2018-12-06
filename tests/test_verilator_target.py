import tempfile
import magma as m
import fault
from bit_vector import BitVector
import common
import random
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
from fault.random import random_bv
import copy
import os.path
import pytest


def test_verilator_trace():
    circ = common.TestBasicClkCircuit
    actions = [
        Poke(circ.I, 0),
        Print(circ.I),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Print(circ.O),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector(1, 1)),
        Eval(),
        Print(circ.O),
    ]
    flags = ["-Wno-lint", "--trace"]

    with tempfile.TemporaryDirectory() as tempdir:
        assert not os.path.isfile(f"{tempdir}/logs/BasicClkCircuit.vcd"), \
            "Expected logs to be empty"
        m.compile(f"{tempdir}/{circ.name}", circ,
                  output="coreir-verilog")
        target = fault.verilator_target.VerilatorTarget(
            circ, directory=f"{tempdir}/",
            flags=flags, skip_compile=True)
        target.run(actions)
        assert os.path.isfile(f"{tempdir}/logs/BasicClkCircuit.vcd"), \
            "Expected VCD to exist"
