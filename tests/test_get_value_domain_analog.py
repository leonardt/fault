import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'spice')


def get_inv_tester(target, vsup):
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

    tester = fault.Tester(dut)
    tester.poke(dut.vdd, vsup)
    tester.poke(dut.vss, 0)
    return dut, tester


def test_edge(target, simulator, vsup=1.8):
    dut, tester = get_inv_tester(target, vsup)

    tester.delay(10e-3)

    # Each horizontal line is 0.5ms (spaces don't count)
    # Input Waveform:  _       _       _         _ _         _ _
    #         ***_ _ _| |_ _ _| |_ _ _| |_ _ _ _|   |_ _ _ _|   |_ ***

    # Output Waveform:
    #            _ _ _   _ _ _   _ _ _   _ _ _ _     _ _ _ _     _
    #         ***     |_|     |_|     |_|       |_ _|       |_ _|  ***
    # get_value:                        ^
    tester.poke(dut.in_, 0, delay=1.5e-3)
    tester.poke(dut.in_, vsup, delay=0.5e-3)
    tester.poke(dut.in_, 0, delay=1.5e-3)
    tester.poke(dut.in_, vsup, delay=0.5e-3)
    tester.poke(dut.in_, 0, delay=1.5e-3)
    tester.poke(dut.in_, vsup, delay=0.5e-3)

    # We add a significant cap load to delay the output slightly,
    # so we only catch the nearby edge when looking forwards
    # default is to look backwards and find rising edges
    a = tester.get_value(dut.out, params={'style': 'edge', 'count': 2})
    a_expect = [-2e-3, -4e-3]
    b = tester.get_value(dut.out,
                         params={'style': 'edge', 'count': 2, 'rising': False})
    b_expect = [-0.5e-3, -2.5e-3]
    c = tester.get_value(dut.out,
                         params={'style': 'edge', 'count': 2, 'forward': True})
    c_expect = [0, 3e-3]
    d = tester.get_value(dut.out,
                         params={'style': 'edge', 'count': 2, 'forward': True,
                                 'rising': False})
    d_expect = [2e-3, 5e-3]

    tester.poke(dut.in_, 0, delay=2e-3)
    tester.poke(dut.in_, vsup, delay=1e-3)
    tester.poke(dut.in_, 0, delay=2e-3)
    tester.poke(dut.in_, vsup, delay=1e-3)
    tester.poke(dut.in_, 0, delay=2e-3)
    tester.poke(dut.in_, vsup, delay=1e-3)

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        vsup=vsup,
        cap_loads={dut.out: 10e-9}
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myinv']

    # run the simulation
    tester.compile_and_run(**kwargs)

    def eq(xs, ys):
        for x, y in zip(xs, ys):
            if abs(x - y) > 5e-5:
                return False
        return True

    print('Measured edge timings:')
    print(a.value)
    print(b.value)
    print(c.value)
    print(d.value)

    assert eq(a.value, a_expect)
    assert eq(b.value, b_expect)
    assert eq(c.value, c_expect)
    assert eq(d.value, d_expect)


def test_phase(target, simulator, vsup=1.5):
    # declare circuit
    mybus = m.DeclareCircuit(
        'mybus',
        'a', m.In(m.Bits[2]),
        'b', m.Out(m.Bits[3]),
        'vdd', m.BitIn,
        'vss', m.BitIn
    )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(mybus)
    else:
        dut = mybus

    # define the test
    tester = fault.Tester(dut)
    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)

    # in[0] gets inverted, in[1] gets buffered
    # I want in[0] to be a 1kHz clock
    # I want in[1] to be a 1kHz clock but delayed by 0.2 ms, so 0.2 cycles
    tester.poke(dut.a[0], 1, delay=0.2e-3)
    tester.poke(dut.a[1], 1, delay=0.3e-3)
    tester.poke(dut.a[0], 0, delay=0.2e-3)
    tester.poke(dut.a[1], 0, delay=0.3e-3)
    tester.poke(dut.a[0], 1, delay=0.2e-3)
    tester.poke(dut.a[1], 1, delay=0.3e-3)
    tester.poke(dut.a[0], 0, delay=0.2e-3)
    tester.poke(dut.a[1], 0, delay=0.3e-3)
    tester.poke(dut.a[0], 1, delay=0.2e-3)
    tester.poke(dut.a[1], 1, delay=0.3e-3)

    a = tester.get_value(dut.a[1], params={'style': 'phase', 'ref': dut.a[0]})
    b = tester.get_value(dut.a[1], params={'style': 'phase', 'ref': dut.b[0]})
    c = tester.get_value(dut.a[0], params={'style': 'phase', 'ref': dut.a[1]})

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/mybus.sp').resolve()],
        vsup=vsup,
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['mybus']

    # run the simulation
    tester.compile_and_run(**kwargs)

    print('Look at measured phases')
    print(a.value)
    print(b.value)
    print(c.value)

    assert abs(a.value - 0.2) < 1e-2
    assert abs(b.value - 0.7) < 1e-2
