import pathlib
import tempfile
import fault
import magma as m
import os
import shutil


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('vcs'):
            targets.append(('system-verilog', 'vcs'))
        if shutil.which('ncsim'):
            targets.append(('system-verilog', 'ncsim'))
        if shutil.which('iverilog'):
            targets.append(('system-verilog', 'iverilog'))
        metafunc.parametrize('target,simulator', targets)


def test_ext_vlog(target, simulator):
    mytb_fname = pathlib.Path('tests/verilog/mytb.sv').resolve()
    tester = fault.Tester(m.DeclareCircuit('mytb'))

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_srcs=[mytb_fname],
            sim_env=sim_env,
            ext_test_bench=True
        )
