import os
import shutil
import random
import tempfile
from pathlib import Path
import magma as m
import fault


def pytest_generate_tests(metafunc):
    if 'target' in metafunc.fixturenames:
        targets = []
        if shutil.which('ncsim'):
            targets.append(('verilog-ams', 'ncsim'))
            targets.append(('system-verilog', 'ncsim'))
        if shutil.which('vcs'):
            targets.append(('system-verilog', 'vcs'))
        if shutil.which('iverilog'):
            targets.append(('system-verilog', 'iverilog'))
        metafunc.parametrize('target,simulator', targets)


def test_mixed_sim(target, simulator, n_trials=100, vsup=1.5):
    # declare the circuit and tester
    ports = []
    ports += ['in_', m.In(m.Bit)]
    ports += ['out', m.Out(m.Bit)]
    if target == 'verilog-ams':
        ports += ['vdd', m.In(m.Bit)]
        ports += ['vss', m.In(m.Bit)]
    dut = m.DeclareCircuit('myinv', *ports)
    tester = fault.Tester(dut)

    # define the test content
    if target == 'verilog-ams':
        tester.poke(dut.vdd, 1)
        tester.poke(dut.vss, 0)

    for _ in range(n_trials):
        # generate random bit
        in_ = random.random() > 0.5

        # send stimulus and check output
        tester.poke(dut.in_, in_)
        tester.eval()
        tester.expect(dut.out, not in_, strict=True)

    # make some environment modifications needed by CAD tools
    # TODO: can this be hidden in a user config file?
    sim_env = fault.util.remove_conda(os.environ)
    sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

    # run the simulation
    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        # generic arguments
        kwargs = dict(target=target,
                      simulator=simulator,
                      directory=tmp_dir,
                      sim_env=sim_env,
                      ext_model_file=True)

        # target-specific options
        if target == 'verilog-ams':
            kwargs['model_paths'] = [Path('tests/spice/myinv.sp').resolve()]
            kwargs['use_spice'] = ['myinv']
            kwargs['vsup'] = vsup
        elif target == 'system-verilog':
            kwargs['ext_libs'] = [Path('tests/verilog/myinv.v').resolve()]

        # compile and run
        tester.compile_and_run(**kwargs)
