"""
Test the construction of expression trees from Peeked values
"""
import shutil
import tempfile

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


def test_and_two_signals(target, simulator):
    """
    Test that we can and two output signals for an expect
    """
    class ANDCircuit(m.Circuit):
        """
        Pass through I0 and I1 as outputs so we can assert a function
        of I0 and I1 as the result
        """
        IO = ["I0", m.In(m.Bits[5]), "I1", m.In(m.Bits[5]),
              "I0_out", m.Out(m.Bits[5]), "I1_out", m.Out(m.Bits[5]),
              "O", m.Out(m.Bits[5])]

        @classmethod
        def definition(io):
            io.I0_out <= io.I0
            io.I1_out <= io.I1
            io.O <= io.I0 & io.I1 

    tester = fault.Tester(ANDCircuit)
    for _ in range(5):
        tester.circuit.I0 = hwtypes.BitVector.random(5)
        tester.circuit.I1 = hwtypes.BitVector.random(5)
        tester.eval()
        tester.circuit.O.expect(tester.circuit.I0_out & tester.circuit.I1_out)

    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "target": target,
            "directory": _dir,
        }
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)
