from pathlib import Path
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_get_value_digital(target, simulator):
    # declare circuit
    myblk = m.DeclareCircuit(
        'myblk',
        'a', m.In(m.Bits[4]),
        'b', m.Out(m.Bits[4]),
        'c', fault.RealIn,
        'd', fault.RealOut
    )

    # define test
    tester = fault.Tester(myblk)

    # provide stimulus
    stim = [(0, 2.34), (1, -4.56), (14, 7.89), (15, 42)]
    output = []
    for a, c in stim:
        tester.poke(myblk.a, a)
        tester.poke(myblk.c, c)
        tester.eval()
        output.append((tester.get_value(myblk.b),
                       tester.get_value(myblk.d)))

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/myblk.sv').resolve()],
        ext_model_file=True,
        tmp_dir=True
    )

    # check the results
    def model(a, c):
        return (a + 1) % 16, 1.23 * c
    for (a, c), (b_meas, d_meas) in zip(stim, output):
        b_expct, d_expct = model(a, c)
        assert b_meas.value == b_expct
        assert (d_expct - 0.01) <= d_meas.value <= (d_expct + 0.01)
