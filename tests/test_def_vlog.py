import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', 'verilator')


def test_def_vlog(target, simulator, n_bits=8, b_val=42):
    # declare circuit
    class defadd(m.Circuit):
        io = m.IO(
            a_val=m.In(m.Bits[n_bits]),
            c_val=m.Out(m.Bits[n_bits])
        )

    # instantiate tester
    tester = fault.Tester(defadd)

    # define test
    tester.poke(defadd.a_val, 12)
    tester.eval()
    tester.expect(defadd.c_val, 54)
    tester.poke(defadd.a_val, 34)
    tester.eval()
    tester.expect(defadd.c_val, 76)

    # define target-specific kwargs
    kwargs = {}
    module_file = Path('tests/verilog/defadd.sv').resolve()
    if target == 'verilator':
        kwargs['ext_model_file'] = module_file
    elif target == 'system-verilog':
        kwargs['simulator'] = simulator
        kwargs['include_verilog_libraries'] = [module_file]
        kwargs['ext_model_file'] = True

    # run simulation
    tester.compile_and_run(
        target=target,
        defines={'N_BITS': n_bits, 'B_VAL': b_val},
        tmp_dir=True,
        **kwargs
    )
