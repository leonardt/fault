import common
import tempfile
from fault import SymbolicTester
from hwtypes import BitVector


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        metafunc.parametrize("target", ["verilator", "cosa"])


def test_tester_magma_internal_signals_verilator(target):
    if target == "cosa":
        from pysmt.shortcuts import Solver
        from pysmt.exceptions import NoSolverAvailableError
        import pytest
        try:
            with Solver(name="msat"):
                pass
        except NoSolverAvailableError:
            pytest.skip("msat not available")
    circ = common.SimpleALU

    tester = SymbolicTester(circ, circ.CLK, num_tests=100)
    tester.circuit.config_en = 1
    tester.circuit.config_data = 0
    tester.step(2)
    # TODO: Handle case with only 1 step in cosa backend, then these would just
    # become assumptions
    tester.circuit.config_en = 0
    tester.step(2)
    if target == "verilator":
        # TODO: We could turn this expect into a CoSA assert
        tester.circuit.config_reg.Q.expect(0)
    tester.circuit.a.assume(lambda a: a < BitVector(32768, 16))
    tester.circuit.b.assume(lambda b: b < BitVector(32768, 16))
    # tester.circuit.b.assume(lambda b: b >= BitVector(32768, 16))

    # tester.circuit.a.assume(lambda a: a < ((1 << 16) - 1))
    # tester.circuit.b.assume(lambda b: b < ((1 << 16) - 1))
    # TODO: Dependent constraints, e.g.
    # tester.ciruit.assume(lambda a, b: a > 0 and b > a)

    # tester.circuit.c.guarantee(lambda x: x > 0)
    tester.circuit.c.guarantee(lambda a, b, c: (c >= a) and (c >= b))
    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {}
        if target == "verilator":
            kwargs["flags"] = ["-Wno-fatal"]
            kwargs["magma_opts"] = {"verilator_debug": True}
        elif target == "cosa":
            kwargs["magma_opts"] = {"passes": ["rungenerators", "flatten",
                                               "cullgraph"]}
        tester.compile_and_run(target, directory=_dir, **kwargs)
