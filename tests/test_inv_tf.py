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


def test_inv_tf(target, simulator, n_steps=25, vsup=1.5):
    # declare circuit and wrap (required if there are in/
    myinv = m.DeclareCircuit('myinv',
                             'in_', fault.RealIn,
                             'out', fault.RealOut,
                             'vdd', fault.RealIn,
                             'vss', fault.RealIn)
    dut = fault.VAMSWrap(myinv)

    tester = fault.Tester(dut)

    tester.poke(dut.vdd, vsup)
    tester.poke(dut.vss, 0)

    for k in range(n_steps):
        tester.poke(dut.in_, k * vsup / (n_steps - 1))
        tester.print("in_=%0f, out=%0f\n", dut.in_, dut.out)

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
