import magma as m
import fault
import tempfile
import pytest
from pathlib import Path
from .common import pytest_sim_params, TestBasicCircuit
import math


def plot(xs, ys):
    import matplotlib.pyplot as plt
    plt.plot(xs, ys, '*')
    plt.grid()
    plt.show()


def pytest_generate_tests(metafunc):
    # Not implemented for verilator because this doesn't make much sense
    # without a concept of delay
    pytest_sim_params(metafunc, 'spice')

# @pytest.mark.skip(reason='Turn this back on later')
def test_sin_spice(target, simulator, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
                   vol_rel=0.1, voh_rel=0.9):
    # declare circuit
    myinv = m.DeclareCircuit(
        'myinv',
        'in_', fault.RealIn,
        'out', fault.RealOut,
        'vdd', fault.RealIn,
        'vss', fault.RealIn
    )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(myinv)
    else:
        dut = myinv

    # define the test
    tester = fault.Tester(dut)
    tester.poke(dut.vdd, vsup)
    tester.poke(dut.vss, 0)
    freq = 1e3
    amp = 0.4
    offset = 0.6
    phase_d = 90
    tester.poke(dut.in_, 0, delay={
        'type': 'sin',
        'freq': freq,
        'amplitude': amp,
        'offset': offset,
        'phase_degrees': phase_d,
        'dt': 1 / (freq * 30)
    })

    def model(x):
        return amp * math.sin(2 * math.pi * freq * x + math.radians(phase_d)) + offset

    num_reads = 100
    xs = []
    dt = 1 / (freq * 50)
    gets = []
    for k in range(num_reads):
        gets.append(tester.get_value(dut.in_))
        tester.delay(dt)
        xs.append(k * dt)

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        vsup=vsup,
        tmp_dir=True,
        clock_step_delay=0
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myinv']

    # run the simulation
    tester.compile_and_run(**kwargs)

    ys = []
    for k in range(num_reads):
        value = gets[k].value
        ys.append(value)
        print('%2d\t' % k, value)

        assert abs(model(xs[k]) - ys[k]) <= amp * 0.25

    #plot(xs, ys)
    #plot(xs, [model(x) for x in xs])
