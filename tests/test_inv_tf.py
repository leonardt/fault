import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilog-ams', 'spice')


def test_inv_tf(
    target, simulator, n_steps=100, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):
    # declare circuit
    class myinv(m.Circuit):
        io = m.IO(
            in_=fault.RealIn,
            out=fault.RealOut,
            vdd=fault.RealIn,
            vss=fault.RealIn
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
    for k in range(n_steps):
        in_ = k * vsup / (n_steps - 1)
        tester.poke(dut.in_, in_)
        tester.eval()
        if in_ <= vil_rel * vsup:
            tester.expect(dut.out, vsup, above=voh_rel * vsup)
        elif in_ >= vih_rel * vsup:
            tester.expect(dut.out, 0, below=vol_rel * vsup)

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
