import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_real_val(target, simulator):
    # define the circuit
    realadd = m.DeclareCircuit(
        'realadd',
        'a_val', fault.RealIn,
        'b_val', fault.RealIn,
        'c_val', fault.RealOut
    )

    # define test content
    tester = fault.Tester(realadd)
    tester.poke(realadd.a_val, 1.125)
    tester.poke(realadd.b_val, 2.5)
    read_a = tester.read(realadd.a_val)
    read_b = tester.read(realadd.b_val)
    read_c = tester.read(realadd.c_val)


    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/realadd.sv').resolve()],
        defines={f'__{simulator.upper()}__': None},
        ext_model_file=True,
        #tmp_dir=True
    )

    a = read_a.value
    b = read_b.value
    c = read_c.value
    assert a == 1.125
    assert b == 2.5
    assert c == 3.625
