import common
import tempfile
from fault import SymbolicTester


def test_tester_magma_internal_signals():
    circ = common.SimpleALU

    tester = SymbolicTester(circ, circ.CLK, num_tests=100)
    tester.circuit.config_en = 1
    tester.circuit.config_data = 0
    tester.step(2)
    tester.circuit.config_reg.Q.expect(0)
    tester.circuit.a.assume(lambda a: a < ((1 << 15)))
    tester.circuit.b.assume(lambda b: b < ((1 << 15)))
    # tester.circuit.a.assume(lambda a: a < ((1 << 16) - 1))
    # tester.circuit.b.assume(lambda b: b < ((1 << 16) - 1))
    # TODO: Dependent constraints, e.g.
    # tester.ciruit.assume(lambda a, b: a > 0 and b > a)

    # tester.circuit.c.guarantee(lambda x: x > 0)
    tester.circuit.c.guarantee(lambda a, b, c: (c >= a) and (c >= b))
    with tempfile.TemporaryDirectory() as _dir:
        _dir = "build"
        tester.compile_and_run("verilator", directory=_dir,
                               flags=["-Wno-fatal"],
                               magma_opts={"verilator_debug": True})
