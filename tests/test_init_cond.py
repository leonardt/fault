import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilog-ams', 'spice')


def test_init_cond(target, simulator, va=1.234, vb=2.345, vc=3.456,
                   abs_tol=1e-3):
    # declare circuit
    class mycirc(m.Circuit):
        name = 'my_init_cond'
        io = m.IO(
            va=fault.RealOut,
            vb=fault.RealOut,
            vc=fault.RealOut
        )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(mycirc)
    else:
        dut = mycirc

    # define the test
    tester = fault.Tester(dut)
    tester.delay(10e-9)
    tester.expect(dut.va, va, abs_tol=abs_tol)
    tester.expect(dut.vb, vb, abs_tol=abs_tol)
    tester.expect(dut.vc, vc, abs_tol=abs_tol)

    # set options
    ic = {
        dut.va: va,
        tester.internal('vb_x'): vb,
        tester.internal('Xe', 'vc_x'): vc
    }
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/my_init_cond.sp').resolve()],
        ic=ic,
        tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['my_init_cond']

    # run the simulation
    tester.compile_and_run(**kwargs)
