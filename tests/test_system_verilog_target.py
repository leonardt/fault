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


def run(circ, actions, flags=[]):
    with tempfile.TemporaryDirectory() as tempdir:
        target = fault.system_verilog_target.SystemVerilogTarget(
            circ, directory=f"{tempdir}/", magma_output="coreir-verilog")
        target.run(actions)


def test_verilator_target_basic():
    """
    Test basic verilator workflow with a simple circuit.
    """
    circ = common.TestBasicCircuit
    actions = (Poke(circ.I, 0), Eval(), Expect(circ.O, 0))
    run(circ, actions)
