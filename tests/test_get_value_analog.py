import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilog-ams', 'spice')


def test_get_value_analog(target, simulator):
    # declare circuit
    myblend = m.DeclareCircuit(
        'myblend',
        'a', fault.RealIn,
        'b', fault.RealIn,
        'c', fault.RealOut,
    )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(myblend)
    else:
        dut = myblend

    # create the tester
    tester = fault.Tester(dut)

    # define the test
    stim = [(5.6, 7.8), (-6.5, -8.7)]
    output = []
    for a, b in stim:
        tester.poke(dut.a, a)
        tester.poke(dut.b, b)
        tester.delay(1e-6)
        output.append(tester.get_value(dut.c))

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myblend.sp').resolve()],
        tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myblend']

    # run the simulation
    tester.compile_and_run(**kwargs)

    # check the results using Python assertions
    def model(a, b):
        return (1.2 * b + 3.4 * a) / (1.2 + 3.4)
    for (a, b), c in zip(stim, output):
        lb = model(a, b) - 0.01
        ub = model(a, b) + 0.01
        assert lb <= c.value <= ub
