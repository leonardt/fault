import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    # Vivado doesn't support the "tran" keyword, so it must be excluded
    pytest_sim_params(metafunc, 'system-verilog', exclude='vivado')


def test_bidir(target, simulator):
    # declare an external circuit that shorts together its two outputs
    class bidir(m.Circuit):
        io = m.IO(
            a=m.InOut(m.Bit),
            b=m.InOut(m.Bit)
        )

    # instantiate the tester
    tester = fault.Tester(bidir, poke_delay_default=0)

    # define common pattern for running all cases
    def run_case(a_in, b_in, a_out, b_out):
        tester.poke(bidir.a, a_in)
        tester.poke(bidir.b, b_in)
        tester.delay(10e-9)
        tester.expect(bidir.a, a_out)
        tester.expect(bidir.b, b_out)

    # walk through all of the cases that produce a 0 or 1 output
    run_case(1, 1, 1, 1)
    run_case(0, 0, 0, 0)
    run_case(1, fault.HiZ, 1, 1)
    run_case(0, fault.HiZ, 0, 0)
    run_case(fault.HiZ, 1, 1, 1)
    run_case(fault.HiZ, 0, 0, 0)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/bidir.v').resolve()],
        ext_model_file=True,
        tmp_dir=True
    )
