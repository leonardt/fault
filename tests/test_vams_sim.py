import os
import shutil
import random
import tempfile
import pathlib
import magma as m
import fault


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('ncsim'):
            targets.append(('verilog-ams', 'ncsim'))
        metafunc.parametrize('target,simulator', targets)


def test_vams_sim(target, simulator, n_trials=100, vsup=1.5):
    myinv_fname = pathlib.Path('tests/spice/myinv.sp').resolve()

    dut = m.DeclareCircuit('myinv',
                           'in_', m.In(m.Bit),
                           'out', m.Out(m.Bit),
                           'vdd', m.In(m.Bit),
                           'vss', m.In(m.Bit))

    tester = fault.Tester(dut)

    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)

    for _ in range(n_trials):
        # generate random bit
        in_ = random.random() > 0.5

        # send stimulus and check output
        tester.poke(dut.in_, in_)
        tester.eval()
        tester.expect(dut.out, not in_, strict=True)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        # Run the simulation
        tester.compile_and_run(target=target,
                               simulator=simulator,
                               directory=tmp_dir,
                               model_paths=[myinv_fname],
                               use_spice=['myinv'],
                               vsup=vsup,
                               sim_env=sim_env,
                               ext_model_file=True)
