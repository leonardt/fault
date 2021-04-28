from pathlib import Path
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    # Not implemented for verilator right now
    # The difficulty is that we have the action print out the simulation time
    # Later we use that time to know where to look in the waveform dump
    # But verilator doesn't have the same concept of simulation time
    pytest_sim_params(metafunc, 'system-verilog')


class MyAdder(m.Circuit):
    io = m.IO(a=m.In(m.UInt[4]),
              b=m.Out(m.UInt[4]))

    io.b @= io.a + 1


def test_get_value_digital(target, simulator):
    # define test
    tester = fault.Tester(MyAdder)

    # provide stimulus
    stim = [2, 3, 2, 3, 2, 3]
    output = []
    freq = 20e6
    for a in stim:
        tester.poke(MyAdder.a, a, delay=(.5/freq))
        tester.eval()
        
    output.append(tester.get_value(MyAdder.b, params={
        'style': 'frequency',
        'height': 3.5
    }))

    # run the test
    kwargs = dict(
        target=target,
    )
    if target == 'system-verilog':
        # This is the only case right now, might do Verilator in the future
        kwargs['simulator'] = simulator
        kwargs['dump_waveforms'] = True
        # tmp_dir seems to break this
        # kwargs['tmp_dir'] = True

    tester.compile_and_run(**kwargs)

    # check the results
    assert freq/1.05 < output[0].value < freq*1.05


def test_real_val(target, simulator):
    # define the circuit
    class RealAdd(m.Circuit):
        io = m.IO(a_val=fault.RealIn, b_val=fault.RealIn, c_val=fault.RealOut)

    # define test content
    # output will toggle between 4 and 8
    stim = [1, 5, 1, 5, 1, 5]
    tester = fault.Tester(RealAdd)
    tester.poke(RealAdd.b_val, 3)
    tester.eval()

    freq = 4e6
    for v in stim:
        tester.poke(RealAdd.a_val, v, delay=1/(2*freq))
        # TODO this eval actually adds a 1ns delay,
        # which breaks this test at higher frequencies
        tester.eval()

    res = tester.get_value(RealAdd.c_val, params={
        'style': 'frequency',
        'height': 6
    })

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/realadd.sv').resolve()],
        defines={f'__{simulator.upper()}__': None},
        ext_model_file=True,
        dump_waveforms=True,
    )
    
    # check the results
    print(freq/1.05, res.value, freq*1.05)
    assert freq/1.05 < res.value < freq*1.05
