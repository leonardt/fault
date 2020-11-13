import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', 'verilator')


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

    # define target-specific kwargs
    kwargs = {}
    module_file = Path('tests/verilog/realadd.sv').resolve()
    if target == 'verilator':
        kwargs['ext_model_file'] = module_file
    elif target == 'system-verilog':
        kwargs['simulator'] = simulator
        kwargs['include_verilog_libraries'] = [module_file]
        kwargs['ext_model_file'] = True
        if simulator == 'iverilog':
            kwargs['defines'] = {'__IVERILOG__': None}

    # run the test
    tester.compile_and_run(
        target=target,
        tmp_dir=True,
        **kwargs
    )
