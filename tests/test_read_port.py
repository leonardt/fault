import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilog-ams', 'spice')


def test_inv_tf(
    target, simulator, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):
    #target = 'verilog-ams'
    #simulator = 'ncsim'
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
    for k in [.4, .5, .6]:
        in_ = k * vsup
        tester.poke(dut.in_, in_)
        # We might not know the expected value now but will want to check later
        tester.expect(dut.out, 0, save_for_later=True)

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
    results = tester.targets[target].saved_for_later
    a, b, c = results
    # now we can save these to a file, post-process them, or use them
    # for our own tests
    assert b <= a, "Inverter tf is not always decreasing"
    assert c <= b, "Inverter tf is not always decreasing"
