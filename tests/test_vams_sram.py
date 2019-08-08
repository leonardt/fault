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
    # declare the circuit
    dut = m.DeclareCircuit('mysram',
                           'wl', m.In(m.Bit),
                           'lbl', m.InOut(m.Bit),
                           'lblb', m.InOut(m.Bit),
                           'vdd', m.In(m.Bit),
                           'vss', m.In(m.Bit))

    # instantiate the tester
    tester = fault.SRAMTester(dut)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # Run the simulation
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        mysram_fname = pathlib.Path('tests/spice/mysram.sp').resolve()
        tester.compile_and_run(target=target,
                               simulator=simulator,
                               directory=tmp_dir,
                               model_paths=[mysram_fname],
                               use_spice=['mysram'],
                               vsup=vsup,
                               sim_env=sim_env,
                               ext_model_file=True)
