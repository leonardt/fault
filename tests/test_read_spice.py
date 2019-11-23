import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    #pytest_sim_params(metafunc, 'verilog-ams', 'spice')
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

def dont_test_inv_tf(
    target, simulator, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):

    # define the test
    dut, tester = get_inv_tester(target, vsup)
    reads = []
    for k in [.4, .5, .6]:
        in_ = k * vsup
        tester.poke(dut.in_, in_)
        # We might not know the expected value now but will want to check later
        read_object = tester.read(dut.out)
        reads.append(read_object)

    tester.poke(dut.in_, vsup, delay=1e-6)
    tester.poke(dut.in_, 0, delay=42e-6)

    edge = tester.read(dut.out, style = 'edge')

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        vsup=vsup,
        tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myinv']

    # run the simulation
    tester.compile_and_run(**kwargs)

    # look at the results we decided to save earlier
    print(reads)
    results = [r.value for r in reads]
    print(results)
    a, b, c = results
    # now we can save these to a file, post-process them, or use them
    # for our own tests
    assert b <= a, "Inverter tf is not always decreasing"
    assert c <= b, "Inverter tf is not always decreasing"

    print(edge.value)

    

def dont_test_edge(
    target, simulator, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):
    dut, tester = get_inv_tester(target, vsup)
    
    tester.poke(dut.in_, 0, delay = 1.5e-3)
    tester.poke(dut.in_, 1, delay = 0.5e-3)
    tester.poke(dut.in_, 0, delay = 1.5e-3)
    tester.poke(dut.in_, 1, delay = 0.5e-3)
    tester.poke(dut.in_, 0, delay = 1.5e-3)
    tester.poke(dut.in_, 1, delay = 0.5e-3)

    a = tester.read(dut.out, style='edge', params={'count':2})
    b = tester.read(dut.out, style='edge', params={'count':2, 'rising':False})
    c = tester.read(dut.out, style='edge', params={'count':2, 'forward':True}) # seems to be counting in 0->1 transitions
    d = tester.read(dut.out, style='edge', params={'count':2, 'forward':True, 'rising':False})

    tester.poke(dut.in_, 0, delay = 0.5e-3)
    tester.poke(dut.in_, 1, delay = 5e-3)
    tester.poke(dut.in_, 0, delay = 5e-3)
    tester.poke(dut.in_, 1, delay = 5e-3)
    tester.poke(dut.in_, 0, delay = 5e-3)
    tester.poke(dut.in_, 1, delay = 5e-3)

    tester.read(dut.in_)

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        vsup=vsup,
        #tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myinv']

    # run the simulation
    tester.compile_and_run(**kwargs)



    def eq(xs, ys):
        print('testing eq')
        print(xs)
        print(ys)
        for x, y in zip(xs, ys):
            if abs(x-y) > 5e-5:
                return False
        return True

    print(eq([1, 2, 3], [1, 2, 3-1e-11]))
    print(eq([1, 2, 3], [1, 2, 3-2e-19]))

    print('TESTING EDGE')
    print(a.value)
    print(b.value)
    print(c.value)
    print(d.value)

    assert eq(a.value, [-0e-3, -2e-3])# TODO should this be [0, 2] ?
    assert eq(b.value, [-0.5e-3, -2.5e-3])
    assert eq(c.value, [5.5e-3, 15.5e-3])
    assert eq(d.value, [0.5e-3, 10.5e-3])
    



def test_phase(
    target, simulator, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):
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
    tester.poke(dut.a[0], 1, delay = 0.2e-3)
    tester.poke(dut.a[1], 1, delay = 0.3e-3)
    tester.poke(dut.a[0], 0, delay = 0.2e-3)
    tester.poke(dut.a[1], 0, delay = 0.3e-3)
    tester.poke(dut.a[0], 1, delay = 0.2e-3)
    tester.poke(dut.a[1], 1, delay = 0.3e-3)
    tester.poke(dut.a[0], 0, delay = 0.2e-3)
    tester.poke(dut.a[1], 0, delay = 0.3e-3)
    tester.poke(dut.a[0], 1, delay = 0.2e-3)
    tester.poke(dut.a[1], 1, delay = 0.3e-3)

    a = tester.read(dut.a[1], style='phase', params={'ref':dut.a[0]})
    b = tester.read(dut.a[1], style='phase', params={'ref':dut.b[0]})
    c = tester.read(dut.a[0], style='phase', params={'ref':dut.a[1]})


    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/mybus.sp').resolve()],
        vsup=vsup,
        #tmp_dir=True
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
    assert abs(c.value - 0.8) < 1e-2
