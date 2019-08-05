import tempfile
import fault
import magma as m
import os
import shutil
import logging
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


def test_def_vlog(target, simulator, n_bits=8, b_val=42):
    # define circuit
    defadd = m.DeclareCircuit('defadd', 'a_val', m.In(m.Bits[n_bits]),
                              'c_val', m.Out(m.Bits[n_bits]))

    # instantiate tester
    tester = fault.Tester(defadd)

    # define test
    tester.poke(defadd.a_val, 12)
    tester.expect(defadd.c_val, 54)
    tester.poke(defadd.a_val, 34)
    tester.expect(defadd.c_val, 76)

    # run the test
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            ext_libs=[Path('tests/verilog/defadd.sv').resolve()],
            sim_env=fault.util.remove_conda(os.environ),
            defines={'N_BITS': n_bits, 'B_VAL': b_val},
            ext_model_file=True
        )
