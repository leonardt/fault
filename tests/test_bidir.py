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


def test_bidir(target, simulator):
    # declare an external circuit that shorts together its two outputs
    bidir_fname = pathlib.Path('tests/verilog/bidir.v').resolve()
    bidir = m.DeclareCircuit('bidir',
                             'a', m.InOut(m.Bit),
                             'b', m.InOut(m.Bit))

    # instantiate the tester
    tester = fault.Tester(bidir)

    # define common pattern for running all cases
    def run_case(a_in, b_in, a_out, b_out):
        tester.poke(bidir.a, a_in)
        tester.poke(bidir.b, b_in)
        tester.expect(bidir.a, a_out, strict=True)
        tester.expect(bidir.b, b_out, strict=True)

    # walk through all of the cases that produce a 0 or 1 output
    run_case(1, 1, 1, 1)
    run_case(0, 0, 0, 0)
    run_case(1, HiZ, 1, 1)
    run_case(0, HiZ, 0, 0)
    run_case(HiZ, 1, 1, 1)
    run_case(HiZ, 0, 0, 0)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[bidir_fname],
            sim_env=sim_env,
            ext_model_file=True
        )
