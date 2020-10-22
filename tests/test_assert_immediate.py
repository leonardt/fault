import pytest

import fault as f
import magma as m


def test_immediate_assert(capsys):
    class Foo(m.Circuit):
        io = m.IO(
            I0=m.In(m.Bit),
            I1=m.In(m.Bit)
        )
        f.assert_immediate(~(io.I0 & io.I1),
                           success_msg="OK",
                           error_msg="FAILED")

    tester = f.Tester(Foo)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    with pytest.raises(AssertionError):
        tester.compile_and_run("verilator")
    print(capsys.out)
    assert False
