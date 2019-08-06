import pathlib
import tempfile
import fault
import magma as m
import os
import shutil
import mantle
from fault import HiZ

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


def test_hi_z(target, simulator):
    # declare an external circuit that shorts together its two outputs
    hizmod_fname = pathlib.Path('tests/verilog/hizmod.v').resolve()
    hizmod = m.DeclareCircuit('hizmod',
                              'a', m.In(m.Bit),
                              'b', m.In(m.Bit),
                              'c', m.Out(m.Bit))

    # instantiate the tester
    tester = fault.Tester(hizmod)

    # define common pattern for running all cases
    def run_case(a, b, c):
        tester.poke(hizmod.a, a)
        tester.poke(hizmod.b, b)
        tester.eval()
        tester.expect(hizmod.c, c, strict=True)

    # walk through all of the cases that produce a 0 or 1 output
    run_case(1, 1, 1)
    run_case(0, 0, 0)
    run_case(1, HiZ, 1) 
    run_case(0, HiZ, 0) 
    run_case(HiZ, 1, 1) 
    run_case(HiZ, 0, 0)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[hizmod_fname],
            sim_env=sim_env,
            ext_model_file=True
        )
