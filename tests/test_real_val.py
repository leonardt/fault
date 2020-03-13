import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_real_val(target, simulator):
    # define the circuit
    class realadd(m.Circuit):
        io = m.IO(
            a_val=fault.RealIn,
            b_val=fault.RealIn,
            c_val=fault.RealOut
        )

    # define test content
    tester = fault.Tester(realadd)
    tester.poke(realadd.a_val, 1.125)
    tester.poke(realadd.b_val, 2.5)
    tester.eval()
    tester.expect(realadd.c_val, 3.625, abs_tol=1e-4)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/vlog w space/realadd.sv').resolve()],
        defines={f'__{simulator.upper()}__': None},
        ext_model_file=True,
        tmp_dir=True
    )
