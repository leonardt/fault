import pathlib
import tempfile
import fault
import magma as m
import os
import shutil
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


def test_real_val(target, simulator):
    realadd_fname = pathlib.Path('tests/verilog/realadd.sv').resolve()
    realadd = m.DeclareCircuit('realadd',
                               'a_val', fault.RealIn,
                               'b_val', fault.RealIn,
                               'c_val', fault.RealOut)

    tester = fault.Tester(realadd)

    tester.poke(realadd.a_val, 1.125)
    tester.poke(realadd.b_val, 2.5)
    tester.expect(realadd.c_val, 3.625, abs_tol=1e-4)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[realadd_fname],
            defines={f'__{simulator.upper()}__': None},
            sim_env=sim_env,
            ext_model_file=True
        )
