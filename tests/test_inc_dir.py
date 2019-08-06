import tempfile
import fault
import magma as m
import os
import shutil
import mantle
from pathlib import Path


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
    mybuf_fname = Path('tests/verilog/mybuf.v').resolve()
    mybuf = m.DeclareCircuit('mybuf', 'in_', m.In(m.Bit), 'out', m.Out(m.Bit))

    tester = fault.Tester(mybuf)

    tester.poke(mybuf.in_, 1)
    tester.eval()
    tester.expect(mybuf.out, 1)

    tester.poke(mybuf.in_, 0)
    tester.eval()
    tester.expect(mybuf.out, 0)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[mybuf_fname],
            inc_dirs=[Path('tests/verilog').resolve()],
            sim_env=sim_env,
            ext_model_file=True
        )
