import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', 'verilator')


def test_def_vlog(target, simulator, n_bits=8, b_val=76):
    # declare circuit
    class paramadd(m.Circuit):
        io = m.IO(
            a_val=m.In(m.Bits[n_bits]),
            c_val=m.Out(m.Bits[n_bits])
        )

    # instantiate tester
    tester = fault.Tester(paramadd)

    # define test
    tester.poke(paramadd.a_val, 98)
    tester.eval()
    tester.expect(paramadd.c_val, 174)
    tester.poke(paramadd.a_val, 54)
    tester.eval()
    tester.expect(paramadd.c_val, 130)

    # define target-specific kwargs
    kwargs = {}
    module_file = Path('tests/verilog/paramadd.sv').resolve()
    if target == 'verilator':
        kwargs['ext_model_file'] = module_file
    elif target == 'system-verilog':
        kwargs['simulator'] = simulator
        kwargs['include_verilog_libraries'] = [module_file]
        kwargs['ext_model_file'] = True

    # run simulation
    tester.compile_and_run(
        target=target,
        parameters={'n_bits': n_bits, 'b_val': b_val},
        tmp_dir=True,
        **kwargs
    )
