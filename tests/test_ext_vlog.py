import pathlib
import tempfile
import fault
import magma as m
import os
import shutil
import logging
import mantle


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
    # logging.getLogger().setLevel(logging.DEBUG)

    myinv_fname = pathlib.Path('tests/verilog/myinv.v').resolve()
    myinv = m.DeclareCircuit('myinv', 'in_', m.In(m.Bit), 'out', m.Out(m.Bit))

    tester = fault.Tester(myinv)

    tester.poke(myinv.in_, 1)
    tester.eval()
    tester.expect(myinv.out, 0)

    tester.poke(myinv.in_, 0)
    tester.eval()
    tester.expect(myinv.out, 1)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[myinv_fname],
            sim_env=sim_env,
            skip_compile=True,
            ext_model_file=True
        )
