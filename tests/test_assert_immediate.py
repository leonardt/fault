from contextlib import nullcontext
import tempfile
import pytest

import fault as f
import magma as m
from fault.verilator_utils import verilator_version
from .test_property import requires_ncsim


@pytest.mark.parametrize('success_msg', [None, "OK"])
@pytest.mark.parametrize('failure_msg', [None, "FAILED"])
@pytest.mark.parametrize('severity', ["error", "fatal", "warning"])
@pytest.mark.parametrize('name', [None, "my_assert"])
def test_immediate_assert(capsys, failure_msg, success_msg, severity,
                          name):
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")
    if failure_msg is not None and severity == "fatal":
        # Verilator won't report failure msg for fatal
        failure_msg = None

    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit),
            O=m.Out(m.Bit)
        )
        io.O @= io.I0 ^ io.I1
        f.assert_immediate(~(io.I0 & io.I1),
                           success_msg=success_msg,
                           failure_msg=failure_msg,
                           severity=severity,
                           name=name)

    tester = f.Tester(Foo)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    tester.eval()
    try:
        with tempfile.TemporaryDirectory() as dir_:
            tester.compile_and_run("verilator", magma_output="mlir-verilog",
                                   flags=['--assert'], directory=dir_,
                                   disp_type="realtime")
    except AssertionError:
        assert failure_msg is None or severity in ["error", "fatal"]
    else:
        assert (
            (severity == "warning") or
            # If success msg but no failure msg, doesn't return error code.
            (failure_msg is None and success_msg is not None)
        )
    out, _ = capsys.readouterr()
    if failure_msg is not None:
        msg = {
            "warning": "%Warning:",
            "fatal": "%Fatal:",
            "error": "%Error:",
        }[severity]
        msg += " Foo.v:9: "
        if verilator_version() >= 5.016:
            if severity == "error":
                msg += "Assertion failed in "
        else:
            msg += "Assertion failed in "
        msg += "TOP.Foo"
        if name is not None:
            msg += f".{name}"
        if failure_msg is not None:
            msg += f": {failure_msg}"
        assert msg in out, out

    tester.clear()
    tester.circuit.I0 = 0
    tester.circuit.I1 = 1
    tester.eval()
    with tempfile.TemporaryDirectory() as dir_:
        tester.compile_and_run("verilator",
                               magma_output="mlir-verilog",
                               flags=['--assert'], directory=dir_,
                               disp_type="realtime")
    out, _ = capsys.readouterr()
    if success_msg is not None:
        assert success_msg in out


def test_immediate_assert_tuple_msg(capsys):
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")

    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit)
        )
        f.assert_immediate(
            io.I0 == io.I1,
            failure_msg=("io.I0 -> %x != %x <- io.I1", io.I0, io.I1)
        )

    tester = f.Tester(Foo)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 0
    tester.eval()
    with pytest.raises(AssertionError):
        with tempfile.TemporaryDirectory() as dir_:
            tester.compile_and_run("verilator", magma_output="mlir-verilog",
                                   flags=['--assert', '-Wno-UNUSED'],
                                   directory=dir_, disp_type="realtime")
    out, _ = capsys.readouterr()
    msg = ("%Error: Foo.v:8: Assertion failed in TOP.Foo: io.I0 -> 1 != 0 <-"
           " io.I1")
    assert msg in out, out


def test_immediate_assert_compile_guard():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")

    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit)
        ) + m.ClockIO()
        io.CLK.unused()
        f.assert_immediate(~(io.I0 & io.I1), compile_guard="ASSERT_ON")

    tester = f.Tester(Foo, Foo.CLK)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    tester.step(2)
    # Should pass without macro defined
    with tempfile.TemporaryDirectory() as dir_:
        tester.compile_and_run("verilator", magma_output="mlir-verilog",
                               flags=['--assert', '-Wno-UNUSED'],
                               directory=dir_, disp_type="realtime")
    # Should fail without macro defined
    with pytest.raises(AssertionError):
        with tempfile.TemporaryDirectory() as dir_:
            tester.compile_and_run(
                "verilator",
                magma_output="mlir-verilog",
                flags=['--assert', '-DASSERT_ON=1', '-Wno-UNUSED'],
                directory=dir_
            )


def test_assert_final():
    class Foo(m.Circuit):
        io = m.IO(
            O=m.Out(m.UInt[2]),
        ) + m.ClockIO()
        count = m.Register(m.UInt[2])()
        count.I @= count.O + 1
        io.O @= count.O
        f.assert_final(count.O == 3)

    tester = f.Tester(Foo, Foo.CLK)
    for i in range(2):
        tester.step(2)
    # Should fail since count is 2
    with pytest.raises(AssertionError):
        with tempfile.TemporaryDirectory() as dir_:
            dir_ = "build"
            tester.compile_and_run("verilator", magma_output="mlir-verilog",
                                   flags=['--assert'], directory=dir_)
    tester.step(2)
    # Should pass since count is 3
    with tempfile.TemporaryDirectory() as dir_:
        tester.compile_and_run("verilator", magma_output="mlir-verilog",
                               flags=['--assert'], directory=dir_)


@requires_ncsim
@pytest.mark.parametrize('should_pass', [True, False])
def test_assert_initial(should_pass):
    class Foo(m.Circuit):
        io = m.IO(O=m.Out(m.UInt[2]))
        x = m.Bits[2](name="x")
        x @= 2
        io.O @= x
        f.assert_initial(x == (2 if should_pass else 1))

    tester = f.Tester(Foo)
    tester.eval()
    with pytest.raises(AssertionError) if not should_pass else nullcontext():
        with tempfile.TemporaryDirectory() as dir_:
            tester.compile_and_run("system-verilog", simulator="ncsim",
                                   magma_output="mlir-verilog",
                                   magma_opts={"sv": True},
                                   directory=dir_)


def test_assert_when():
    if verilator_version() < 4.0:
        pytest.skip("Untested with earlier verilator versions")

    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit),
            S=m.In(m.Bit)
        )
        with m.when(io.S):
            f.assert_immediate(~(io.I0 & io.I1))

    tester = f.Tester(Foo)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    tester.circuit.S = 1
    tester.eval()
    with tempfile.TemporaryDirectory() as dir_:
        with pytest.raises(AssertionError):
            tester.compile_and_run("verilator",
                                   magma_output="mlir-verilog",
                                   flags=['--assert'], directory=dir_,
                                   disp_type="realtime")

        tester.clear()
        tester.circuit.I0 = 1
        tester.circuit.I1 = 1
        tester.eval()
        tester.compile_and_run("verilator",
                               magma_output="mlir-verilog",
                               flags=['--assert'], directory=dir_,
                               skip_compile=True,
                               disp_type="realtime")
