import magma as m
import fault
from pathlib import Path
#from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'spice')


def test_get_value_analog(target, simulator):
    # declare circuit
    class mycurrenttest(m.Circuit):
        io = m.IO(
            in_c=fault.CurrentIn,
            in_v=fault.RealIn,
            out_c=fault.CurrentOut,
            out_v=fault.RealOut
        )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(mycurrenttest)
    else:
        dut = mycurrenttest

    # create the tester
    tester = fault.Tester(dut)

    # define the test
    stim = [(5.6, 7.8), (-6.5, -8.7)]
    output = []
    for a, b in stim:
        tester.poke(dut.in_c, a)
        tester.poke(dut.in_v, b)
        tester.delay(1e-6)
        output.append((tester.get_value(dut.out_c),
                       tester.get_value(dut.out_v)))

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        tmp_dir=False
    )
    spice_model = Path('tests/spice/mycurrenttest.sp').resolve()
    if target == 'verilog-ams':
        kwargs['model_paths'] = [spice_model]
        kwargs['use_spice'] = ['mycurrenttest']
    elif target == 'spice':
        kwargs['model_paths'] = [spice_model]

    # run the simulation
    tester.compile_and_run(**kwargs)

    # check the results using Python assertions
    def model(a, b):
        return (b / 100, a*500)

    for (a, b), (c, d) in zip(stim, output):
        for expected, read in zip(model(a, b), (c, d)):
            lb = expected - 0.01
            ub = expected + 0.01
            print('Asserting', lb, read.value, ub)
            assert lb <= read.value <= ub


if __name__ == '__main__':
    test_get_value_analog('spice', 'ngspice')
