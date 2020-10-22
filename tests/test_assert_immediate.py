import tempfile
import pytest

import fault as f
import magma as m


@pytest.mark.parametrize('success_msg', [None, "OK"])
@pytest.mark.parametrize('failure_msg', [None, "FAILED"])
@pytest.mark.parametrize('severity', ["error", "fatal", "warning"])
def test_immediate_assert(capsys, failure_msg, success_msg, severity):
    if failure_msg is not None and severity == "fatal":
        # Use integer exit code
        failure_msg = 1

    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit)
        )
        f.assert_immediate(~(io.I0 & io.I1),
                           success_msg=success_msg,
                           failure_msg=failure_msg,
                           severity=severity)

    tester = f.Tester(Foo)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    tester.eval()
    try:
        with tempfile.TemporaryDirectory() as dir_:
            tester.compile_and_run("verilator", magma_opts={"inline": True},
                                   flags=['--assert'], directory=dir_,
                                   disp_type="realtime")
    except AssertionError:
        assert failure_msg is None or severity in ["error", "fatal"]
    else:
        # warning doesn't trigger exit code/failure (but only if there's a
        # failure_msg, otherwise severity is ignored)
        assert severity == "warning"
    out, _ = capsys.readouterr()
    if failure_msg is not None:
        if severity == "warning":
            msg = "%Warning:"
        else:
            msg = "%Error:"
        msg += " Foo.v:13: Assertion failed in TOP.Foo"
        if severity == "error":
            msg += f": {failure_msg}"
        assert msg in out

    tester.clear()
    tester.circuit.I0 = 0
    tester.circuit.I1 = 1
    tester.eval()
    with tempfile.TemporaryDirectory() as dir_:
        tester.compile_and_run("verilator", magma_opts={"inline": True},
                               flags=['--assert'], directory=dir_,
                               disp_type="realtime")
    out, _ = capsys.readouterr()
    if success_msg is not None:
        assert success_msg in out
