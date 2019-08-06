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


def test_def_vlog(target, simulator, n_bits=8, b_val=42):
    defadd_fname = pathlib.Path('tests/verilog/defadd.sv').resolve()
    defadd = m.DeclareCircuit('defadd', 'a_val', m.In(m.Bits[n_bits]),
                              'c_val', m.Out(m.Bits[n_bits]))

    tester = fault.Tester(defadd)

    tester.poke(defadd.a_val, 12)
    tester.eval()
    tester.expect(defadd.c_val, 54)

    tester.poke(defadd.a_val, 34)
    tester.eval()
    tester.expect(defadd.c_val, 76)

    # make some modifications to the environment
    sim_env = fault.util.remove_conda(os.environ)

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[defadd_fname],
            sim_env=sim_env,
            defines={'N_BITS': n_bits, 'B_VAL': b_val},
            ext_model_file=True
        )
