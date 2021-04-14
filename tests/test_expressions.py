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


def run_test(tester, target, simulator):
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {
            "target": target,
            "directory": _dir
        }
        if target == "system-verilog":
            kwargs["simulator"] = simulator
        tester.compile_and_run(**kwargs)


def gen_binary_op_circuit(op):
    class BinaryOpCircuit(m.Circuit):
        """
        Pass through I0 and I1 as outputs so we can assert a function
        of I0 and I1 as the result
        """
        if op in {"lt", "le", "gt", "ge", "ne", "eq"}:
            Out_T = m.Bit
        else:
            Out_T = m.UInt[5]
        io = m.IO(I0=m.In(m.UInt[5]), I1=m.In(m.UInt[5]),
                  I0_out=m.Out(m.UInt[5]), I1_out=m.Out(m.UInt[5]),
                  O=m.Out(Out_T))

        io.I0_out @= io.I0
        io.I1_out @= io.I1
        m.wire(io.O, getattr(operator, op)(io.I0, io.I1))
    return BinaryOpCircuit


def gen_random_inputs(op):
    I0 = hwtypes.BitVector.random(5)
    if op in {"lshift", "truediv"}:
        # avoid C overflow exception
        I1 = hwtypes.BitVector.random(2)
        if op == "truediv":
            pytest.skip("Need to generate random numbers that don't trigger a C exception")  # noqa
            while I1 == 0:
                I1 = hwtypes.BitVector.random(2)
    else:
        I1 = hwtypes.BitVector.random(5)
    return I0, I1


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
def test_binop_two_signals_setattr(target, simulator, op):
    """
    Test that we can and two output signals for an expect
    """
    if op == "mod":
        pytest.skip("urem missing from coreir verilog backend")

    BinaryOpCircuit = gen_binary_op_circuit(op)

    tester = fault.Tester(BinaryOpCircuit)
    for _ in range(5):
        I0, I1 = gen_random_inputs(op)
        tester.circuit.I0 = I0
        tester.circuit.I1 = I1
        tester.eval()
        tester.circuit.O.expect(getattr(operator, op)(tester.circuit.I0_out,
                                                      tester.circuit.I1_out))
        tester.circuit.O.expect(getattr(operator, op)(tester.circuit.I0,
                                                      tester.circuit.I1))

    run_test(tester, target, simulator)


@pytest.mark.parametrize("op", ["add", "truediv", "and_", "xor", "or_",
                                "lshift", "rshift", "mod", "mul", "rshift",
                                "sub", "lt", "le", "eq", "ne", "gt", "ge"])
def test_binop_two_signals_raw(target, simulator, op):
    """
    Test that we can and two output signals for an expect
    """
    if op == "mod":
        pytest.skip("urem missing from coreir verilog backend")

    BinaryOpCircuit = gen_binary_op_circuit(op)

    tester = fault.Tester(BinaryOpCircuit)
    for _ in range(5):
        I0, I1 = gen_random_inputs(op)
        tester.poke(tester._circuit.I0, I0)
        tester.poke(tester._circuit.I1, I1)
        tester.eval()
        tester.expect(
            tester._circuit.O,
            getattr(operator, op)(tester.peek(tester._circuit.I0_out),
                                  tester.peek(tester._circuit.I1_out)))

    run_test(tester, target, simulator)


def test_op_tree(target, simulator):
    class BinaryOpCircuit(m.Circuit):
        """
        Pass through I0 and I1 as outputs so we can assert a function
        of I0 and I1 as the result
        """
        io = m.IO(I0=m.In(m.UInt[5]), I1=m.In(m.UInt[5]),
                  I0_out=m.Out(m.UInt[5]), I1_out=m.Out(m.UInt[5]),
                  O=m.Out(m.UInt[5]))

        io.I0_out @= io.I0
        io.I1_out @= io.I1
        m.wire(io.O, io.I0 + io.I1 & (io.I1 - io.I0))

    tester = fault.Tester(BinaryOpCircuit)
    for _ in range(5):
        tester.poke(tester._circuit.I0, hwtypes.BitVector.random(5))
        tester.poke(tester._circuit.I1, hwtypes.BitVector.random(5))
        tester.eval()
        expected = tester.peek(tester._circuit.I0_out) + \
            tester.peek(tester._circuit.I1_out)
        expected &= tester.peek(tester._circuit.I1_out) - \
            tester.peek(tester._circuit.I0_out)
        tester.expect(tester._circuit.O, expected)
        expected = tester.peek(tester._circuit.I0) + \
            tester.peek(tester._circuit.I1)
        expected &= tester.peek(tester._circuit.I1) - \
            tester.peek(tester._circuit.I0)
        tester.expect(tester._circuit.O, expected)

    run_test(tester, target, simulator)


def test_abs(target, simulator):
    if simulator == "iverilog":
        pytest.skip("$abs does not work as expected with iverilog")

    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.SInt[2]), O=m.Out(m.SInt[2]))
        io.O @= io.I

    tester = fault.Tester(Foo)
    tester.circuit.I = expect = 1
    tester.eval()
    # abs(1 - 1) == 0
    tester.assert_(fault.abs(fault.signed(tester.circuit.O) - expect) <= 1)
    tester.circuit.I = 0
    expect = 1
    tester.eval()
    # abs(0 - 1) == 1
    tester.assert_(fault.abs(fault.signed(tester.circuit.O) - expect) <= 1)
    run_test(tester, target, simulator)

    # test failure case
    expect = 2
    # abs(0 - 2) == 2
    tester.assert_(fault.abs(fault.signed(tester.circuit.O) - expect) <= 1)
    with pytest.raises(AssertionError):
        run_test(tester, target, simulator)


def test_min(target, simulator):
    if simulator == "iverilog":
        pytest.skip("int casting does not work with iverilog")
    if simulator == "ncsim":
        pytest.skip("ncsim does not define $min")

    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.SInt[2]), O=m.Out(m.SInt[2]))
        io.O @= io.I

    tester = fault.Tester(Foo)
    tester.circuit.I = 1
    tester.eval()
    tester.assert_(fault.min(fault.integer(tester.circuit.O), 0) == 0)
    tester.assert_(fault.min(fault.integer(tester.circuit.O), 2) == 1)
    run_test(tester, target, simulator)

    tester.assert_(fault.min(fault.integer(tester.circuit.O), 2) == 2)
    with pytest.raises(AssertionError):
        run_test(tester, target, simulator)


def test_max(target, simulator):
    if simulator == "iverilog":
        pytest.skip("int casting does not work with iverilog")
    if simulator == "ncsim":
        pytest.skip("ncsim does not define $max")

    class Foo(m.Circuit):
        io = m.IO(I=m.In(m.SInt[2]), O=m.Out(m.SInt[2]))
        io.O @= io.I

    tester = fault.Tester(Foo)
    tester.circuit.I = 1
    tester.eval()
    tester.assert_(fault.max(fault.integer(tester.circuit.O), 0) == 1)
    tester.assert_(fault.max(fault.integer(tester.circuit.O), 2) == 2)
    run_test(tester, target, simulator)

    tester.assert_(fault.max(fault.integer(tester.circuit.O), 2) == 1)
    with pytest.raises(AssertionError):
        run_test(tester, target, simulator)


def test_rand():
    f = fault

    class Foo(m.Circuit):
        io = m.IO(
            read_valid=m.In(m.Bit),
            read_array=m.In(m.Bits[8]),
            iter_req=m.In(m.Bits[2])
        ) + m.ClockIO()

        f.cover(io.read_valid & (f.countones(io.read_array) == io.iter_req),
                on=f.posedge(io.CLK))

    m.compile("build/Foo", Foo)
