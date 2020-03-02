import tempfile
from ..common import AndCircuit, pytest_sim_params
import fault


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


def test_call_interface_basic(target, simulator):
    tester = fault.Tester(AndCircuit)
    for i, j in zip(range(2), range(2)):
        tester(i, j).expect(i & j)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir)
        else:
            tester.compile_and_run(target, directory=_dir,
                                   simulator=simulator)
