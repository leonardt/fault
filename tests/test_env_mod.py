import pathlib
import tempfile
import fault
import magma as m
import os
import shutil
import logging
import mantle


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = []
        if shutil.which("vcs"):
            targets.append(("system-verilog", "vcs"))
        if shutil.which("ncsim"):
            targets.append(("system-verilog", "ncsim"))
        metafunc.parametrize("target,simulator", targets)


def test_env_mod(target, simulator):
    # logging.getLogger().setLevel(logging.DEBUG)

    myinv = m.DefineCircuit('myinv', 'a', m.In(m.Bit), 'y', m.Out(m.Bit))
    m.wire(~myinv.a, myinv.y)
    m.EndDefine()

    tester = fault.Tester(myinv)

    tester.poke(myinv.a, 1)
    tester.eval()
    tester.expect(myinv.y, 0)
    tester.poke(myinv.a, 0)
    tester.eval()
    tester.expect(myinv.y, 1)

    with tempfile.TemporaryDirectory(dir='.') as tmp_dir:
        # make some modifications to the environment
        sim_env = fault.util.remove_conda(os.environ)
        sim_env['DISPLAY'] = sim_env.get('DISPLAY', '')

        # run the test
        tester.compile_and_run(
            target=target,
            simulator=simulator,
            directory=tmp_dir,
            sim_env=sim_env
        )
