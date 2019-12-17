import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_def_vlog(target, simulator, n_bits=8, b_val=76):
    # declare circuit
    paramadd = m.DeclareCircuit(
        'paramadd',
        'a_val', m.In(m.Bits[n_bits]),
        'c_val', m.Out(m.Bits[n_bits])
    )

    # instantiate tester
    tester = fault.Tester(paramadd)

    # define test
    tester.poke(paramadd.a_val, 98)
    tester.step()
    tester.expect(paramadd.c_val, 174)
    tester.poke(paramadd.a_val, 54)
    tester.step()
    tester.expect(paramadd.c_val, 130)

    # run simulation
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/paramadd.sv').resolve()],
        parameters={'n_bits': n_bits, 'b_val': b_val},
        ext_model_file=True,
        tmp_dir=True
    )
