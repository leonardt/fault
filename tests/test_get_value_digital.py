from pathlib import Path
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', 'verilator')


class MyAdder(m.Circuit):
    io = m.IO(a=m.In(m.UInt[4]),
              b=m.Out(m.UInt[4]))

    io.b @= io.a + 1


def test_get_value_digital(target, simulator):
    # define test
    tester = fault.Tester(MyAdder)

    # provide stimulus
    stim = list(range(16))
    output = []
    for a in stim:
        tester.poke(MyAdder.a, a)
        tester.eval()
        output.append(tester.get_value(MyAdder.b))

    # run the test
    kwargs = dict(
        target=target,
        tmp_dir=True
    )
    if target == 'system-verilog':
        kwargs['simulator'] = simulator
    elif target == 'verilator':
        kwargs['flags'] = ['-Wno-fatal']
    tester.compile_and_run(**kwargs)

    # check the results
    def model(a):
        return (a + 1) % 16
    for a, b_meas in zip(stim, output):
        b_expct = model(a)
        assert b_meas.value == b_expct
