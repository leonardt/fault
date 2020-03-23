from pathlib import Path
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')
    # TODO I don't think this works in verilator yet?
    #pytest_sim_params(metafunc, 'system-verilog', 'verilator')


class MyAdder(m.Circuit):
    io = m.IO(a=m.In(m.UInt[4]),
              b=m.Out(m.UInt[4]))

    io.b @= io.a + 1


def test_get_value_digital(target, simulator):
    # TODO get rid of this when we test on a system with things installed
    #target = 'system-verilog'
    simulator = 'ncsim'
    
    # define test
    tester = fault.Tester(MyAdder)

    # provide stimulus
    stim = [2, 3, 2, 3, 2, 3]
    output = []
    freq = 20e6
    for a in stim:
        tester.poke(MyAdder.a, a, delay=(.5/freq))
        tester.eval()
        
    output.append(tester.get_value(MyAdder.b, params = {
        'style': 'frequency',
        'height': 3.5
    }))
        
    

    # run the test
    kwargs = dict(
        target=target,
        #tmp_dir=True
    )
    if target == 'system-verilog':
        kwargs['simulator'] = simulator
    elif target == 'verilator':
        kwargs['flags'] = ['-Wno-fatal']
    tester.compile_and_run(**kwargs)

    # check the results
    assert freq/1.05 < output[0].value < freq*1.05


def test_real_val(target, simulator):
    simulator = 'ncsim'
    # define the circuit
    class realadd(m.Circuit):
        io = m.IO(a_val=fault.RealIn, b_val=fault.RealIn, c_val=fault.RealOut)

    # define test content
    stim = [1, 5, 1, 5, 1, 5]
    tester = fault.Tester(realadd)
    tester.poke(realadd.b_val, 3)
    tester.eval()

    for v in stim:
        tester.poke(realadd.a_val, v, delay=125e-9)
        tester.eval()

    res = tester.get_value(realadd.c_val, params = {
        'style' : 'frequency',
        'height' : 6
    })

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/realadd.sv').resolve()],
        defines={f'__{simulator.upper()}__': None},
        ext_model_file=True,
        #tmp_dir=True
    )
    
    print(res.value)
