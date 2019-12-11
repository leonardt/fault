import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    # Vivado doesn't support the "tran" keyword, so it must be excluded
    pytest_sim_params(metafunc, 'system-verilog', exclude='vivado')


def test_hi_z(target, simulator):
    # declare an external circuit that shorts together its two outputs
    hizmod = m.DeclareCircuit(
        'hizmod',
        'a', m.In(m.Bit),
        'b', m.In(m.Bit),
        'c', m.Out(m.Bit)
    )

    # instantiate the tester
    tester = fault.Tester(hizmod)

    # define common pattern for running all cases
    def run_case(a, b, c):
        tester.poke(hizmod.a, a)
        tester.poke(hizmod.b, b)
        tester.expect(hizmod.c, c, strict=True)

    # walk through all of the cases that produce a 0 or 1 output
    run_case(1, 1, 1)
    run_case(0, 0, 0)
    run_case(1, fault.HiZ, 1)
    run_case(0, fault.HiZ, 0)
    run_case(fault.HiZ, 1, 1)
    run_case(fault.HiZ, 0, 0)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/hizmod.v').resolve()],
        ext_model_file=True,
        tmp_dir=True
    )
