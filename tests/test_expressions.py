"""
Test the construction of expression trees from Peeked values
"""
import shutil
import tempfile
import operator
import pytest

import fault
import magma as m
import mantle
import hwtypes


def pytest_generate_tests(metafunc):
    """
    Parametrize tests over targets
    """
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if shutil.which("irun"):
            targets.append(
                ("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(
                ("system-verilog", "vcs"))
        if shutil.which("iverilog"):
            targets.append(
                ("system-verilog", "iverilog"))
        metafunc.parametrize("target,simulator", targets)


@pytest.mark.parametrize("op", ["add", "truediv", "and_", "xor", "or_",
                                "lshift", "rshift", "mod", "mul", "rshift",
                                "sub", "lt", "le", "eq", "ne", "gt", "ge"])
def test_binop_two_signals(target, simulator, op):
    """
    Test that we can and two output signals for an expect
    """
    if op == "mod":
        pytest.skip("urem missing from coreir verilog backend")

    class BinaryOpCircuit(m.Circuit):
        """
        Pass through I0 and I1 as outputs so we can assert a function
        of I0 and I1 as the result
        """
        IO = ["I0", m.In(m.UInt[5]), "I1", m.In(m.UInt[5]),
              "I0_out", m.Out(m.UInt[5]), "I1_out", m.Out(m.UInt[5]) ]
        if op in {"lt", "le", "gt", "ge", "ne", "eq"}:
            IO += ["O", m.Out(m.Bit)]
        else:
            IO += ["O", m.Out(m.UInt[5])]

        @classmethod
        def definition(io):
            io.I0_out <= io.I0
            io.I1_out <= io.I1
            m.wire(io.O, getattr(operator, op)(io.I0, io.I1))

    tester = fault.Tester(BinaryOpCircuit)
    for _ in range(5):
        tester.circuit.I0 = hwtypes.BitVector.random(5)
        if op == "lshift":
            # avoid C overflow exception
            tester.circuit.I1 = hwtypes.BitVector.random(2)
        else:
            tester.circuit.I1 = hwtypes.BitVector.random(5)
        tester.eval()
        tester.circuit.O.expect(getattr(operator, op)(tester.circuit.I0_out,
                                                      tester.circuit.I1_out))

    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "target": target,
            "directory": _dir,
        }
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)
