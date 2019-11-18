import magma as m
import fault
import tempfile
import pytest
from pathlib import Path
from .common import pytest_sim_params, TestBasicCircuit

def plot(xs, ys):
    import matplotlib.pyplot as plt
    plt.plot(xs, ys, '*')
    plt.grid()
    plt.show()

def pytest_generate_tests(metafunc):
    #pytest_sim_params(metafunc, 'verilator', 'system-verilog')
    #pytest_sim_params(metafunc, 'spice')
    pytest_sim_params(metafunc, 'system-verilog')

#@pytest.mark.skip(reason='Not yet implemented')
def test_clock_verilog(target, simulator):
    print('target, sim', target, simulator)
    # TODO delete the next line; my iverilog is just broken so I can't test it
    simulator = 'ncsim'
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    #tester.eval()
    tester.expect(circ.O, 1)

    # register clock
    tester.poke(circ.I, 0, delay={
        'freq': 0.125,
        'duty_cycle': 0.625,
        # take default initial_value of 0
        })

    tester.expect(circ.O, 1) # should fail
    tester.expect(circ.O, 0) # should fail


    tester.expect(circ.O, 0, save_for_later=True)


    tester.print("%08x", circ.O)

    
    #with tempfile.TemporaryDirectory(dir=".") as _dir:
    #with open('build/') as _dir:
    if True:
        _dir = 'build'
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"])
        else:
            tester.compile_and_run(target, directory=_dir, simulator=simulator)
    print('JUST FINISHED COMPILENANDRUN')


@pytest.mark.skip(reason='Turn this back on later')
def test_sin_spice(vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9):
    # TODO make pytest choose target/simulator
    target = 'spice'
    simulator = 'ngspice'
    


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
    tester.poke(dut.in_, 0, delay = {
        'type': 'sin',
        'freq': freq,
        'amplitude': 0.4,
        'offset': 0.6,
        'phase_degrees': 90
        })

    num_reads = 100
    xs = []
    dt = 1/(freq * 50)
    for k in range(num_reads):
        tester.expect(dut.in_, 0, save_for_later=True)
        tester.delay(dt)
        xs.append(k*dt)

    #for k in [.4, .5, .6]:
    #    in_ = k * vsup
    #    tester.poke(dut.in_, in_)
    #    # We might not know the expected value now but will want to check later
    #    tester.expect(dut.out, 0, save_for_later=True)

    

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        vsup=vsup,
        tmp_dir=True,
        clock_step_delay = 0
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['myinv']

    # run the simulation
    tester.compile_and_run(**kwargs)

    ys = []
    for k in range(num_reads):
        value = tester.targets[target].saved_for_later[k]
        ys.append(value)
        print('%2d\t'%k, value)

    plot(xs, ys)
