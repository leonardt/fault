import os
import shutil
import random
import tempfile
import magma as m
import fault
from pathlib import Path


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('ncsim'):
            targets.append(('verilog-ams', 'ncsim'))
        metafunc.parametrize('target,simulator', targets)


def test_inv_tf(target, simulator, n_steps=25, vsup=1.5,
                vil_rel=0.4, vih_rel=0.6):
    # declare circuit and wrap 
    myinv = m.DeclareCircuit('myinv',
                             'in_', fault.RealIn,
                             'out', fault.RealOut,
                             'vdd', fault.RealIn,
                             'vss', fault.RealIn)
    dut = fault.VAMSWrap(myinv)

    tester = fault.Tester(dut)

    # define the test
    tester.poke(dut.vdd, vsup)
    tester.poke(dut.vss, 0)
    for k in range(n_steps):
        in_ = k * vsup / (n_steps - 1)
        tester.poke(dut.in_, in_)
        if in_ <= vil_rel*vsup:
            tester.expect(dut.out, vsup, abs_tol=0.1)
        elif in_ >= vih_rel*vsup:
            tester.expect(dut.out, 0, abs_tol=0.1)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # resolve location of inverter spice file
    myinv_fname = Path('tests/spice/myinv.sp').resolve()

    # run the simulation
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(target=target,
                               simulator=simulator,
                               directory=tmp_dir,
                               model_paths=[myinv_fname],
                               use_spice=['myinv'],
                               vsup=vsup,
                               sim_env=sim_env)
