import tempfile

import pytest

from hwtypes import BitVector

import magma as m

from fault import SymbolicTester

from ..common import ConfigReg


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        metafunc.parametrize("target", ["verilator", "pono"])


class SimpleALU(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              c=m.Out(m.UInt[16]),
              config_data=m.In(m.Bits[2]),
              config_en=m.In(m.Enable),
              ) + m.ClockIO()

    opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
    io.c @= m.mux(
        [io.a - io.b, io.a + io.b, io.a * io.b, io.b / io.a], opcode)


def test_tester_magma_internal_signals_verilator(target):
    if target == "pono":
        try:
            from smt_switch.primops import BVUge, And, BVUlt
            import pono
            # Use symbols to avoid unused symbols lint warning
            pono
        except ImportError:
            pytest.skip("Could not import pono or smt_switch")

        # TODO: Fix test
        # https://github.com/leonardt/fault/runs/2347548425
        # maybe it's using an old API?
        pytest.skip("Could not import pono or smt_switch")
    circ = SimpleALU

    tester = SymbolicTester(circ, circ.CLK, num_tests=100)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    tester.circuit.config_data = 1  # add is opcode 2
    tester.step(2)
    tester.circuit.config_en = 0
    tester.step(2)
    tester.circuit.config_en = 0
    tester.step(2)
    if target == "verilator":
        # TODO: We could turn this expect into a property
        tester.circuit.config_reg.Q.expect(1)
        tester.circuit.a.assume(lambda a: a < BitVector[16](32768))
        tester.circuit.b.assume(lambda b: b < BitVector[16](32768))
        tester.circuit.c.guarantee(lambda a, b, c: (c >= a) and (c >= b))
    else:
        tester.circuit.a.assume(
            lambda solver, a, sort: solver.make_term(BVUlt, a,
                                                     solver.make_term(32768,
                                                                      sort))
        )
        tester.circuit.b.assume(
            lambda solver, b, sort: solver.make_term(BVUlt, b,
                                                     solver.make_term(32768,
                                                                      sort))
        )
        tester.circuit.c.guarantee(
            lambda solver, ports:
            solver.make_term(
                And,
                solver.make_term(BVUge, ports['c'], ports['a']),
                solver.make_term(BVUge, ports['c'], ports['b']),
            )
        )

    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {}
        if target == "verilator":
            kwargs["magma_opts"] = {"verilator_debug": True,
                                    "verilator_compat": True}
        tester.compile_and_run(target, directory=_dir, **kwargs)
