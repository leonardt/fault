import os
import shutil
import random
import tempfile
import pathlib
import magma as m
import fault
from fault import HiZ


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('ncsim'):
            targets.append(('verilog-ams', 'ncsim'))
        metafunc.parametrize('target,simulator', targets)


def test_vams_sim(target, simulator, n_trials=100, vsup=1.5):
    mysram_fname = pathlib.Path('tests/spice/mysram.sp').resolve()

    dut = m.DeclareCircuit('mysram',
                           'wl', m.In(m.Bit),
                           'lbl', m.InOut(m.Bit),
                           'lblb', m.InOut(m.Bit),
                           'vdd', m.In(m.Bit),
                           'vss', m.In(m.Bit))

    tester = fault.Tester(dut)

    # initialize pin values
    tester.poke(dut.wl, 0)
    tester.poke(dut.lbl, 0)
    tester.poke(dut.lblb, 0)
    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)

    for _ in range(n_trials):
        # generate random input
        d = random.random() > 0.5

        # write value
        tester.poke(dut.lbl, d)
        tester.poke(dut.lblb, not d)
        tester.poke(dut.wl, 1)
        tester.poke(dut.wl, 0)

        # read value
        tester.poke(dut.lbl, HiZ)
        tester.poke(dut.lblb, HiZ)
        tester.poke(dut.wl, 1)
        tester.expect(dut.lbl, d, strict=True)
        tester.expect(dut.lblb, not d, strict=True)
        tester.poke(dut.wl, 0)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # Run the simulation
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(target=target,
                               simulator=simulator,
                               directory=tmp_dir,
                               model_paths=[mysram_fname],
                               use_spice=['mysram'],
                               vsup=vsup,
                               sim_env=sim_env,
                               ext_model_file=True)
