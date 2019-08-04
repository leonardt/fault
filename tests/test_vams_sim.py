import os
import shutil
import random
import tempfile
import logging
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
    # logging.getLogger().setLevel(logging.DEBUG)

    myinv_fname = pathlib.Path('tests/spice/myinv.sp').resolve()

    myinv = m.DeclareCircuit('myinv',
                             'in_', fault.AnalogIn,
                             'out', fault.AnalogOut,
                             'vdd', fault.AnalogIn,
                             'vss', fault.AnalogIn)

    dut = fault.VAMSWrap(myinv)

    tester = fault.Tester(dut)

    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)

    for _ in range(n_trials):
        # generate random bit
        if random.random() > 0.5:
            in_ = 1
        else:
            in_ = 0

        # send stimulus and check output
        tester.poke(dut.in_, in_)
        tester.eval()
        tester.expect(dut.out, not in_)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        # Write the Verilog-AMS model
        vamsf = os.path.join(tmp_dir, 'myinv_wrap.vams')
        vamsf = os.path.realpath(os.path.expanduser(vamsf))
        open(vamsf, 'w').write(dut.vams_code)

        # Run the simulation
        tester.compile_and_run(target=target,
                               simulator=simulator,
                               directory=tmp_dir,
                               model_paths=[myinv_fname],
                               ext_libs=[vamsf],
                               sim_env=sim_env,
                               skip_compile=True,
                               ext_model_file=True,
                               vsup=vsup)
