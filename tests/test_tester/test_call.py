import tempfile
from ..common import AndCircuit, pytest_sim_params, SimpleALU
import fault
import operator
from hwtypes import BitVector


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
                                   simulator=simulator,
                                   magma_opts={"sv": True})


def test_call_interface_kwargs(target, simulator):
    tester = fault.Tester(AndCircuit)
    for i, j in zip(range(2), range(2)):
        tester(i, j, I0=0).expect(0)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir)
        else:
            tester.compile_and_run(target, directory=_dir,
                                   simulator=simulator,
                                   magma_opts={"sv": True})


def test_call_interface_kwargs(target, simulator):
    tester = fault.Tester(AndCircuit)
    for i, j in zip(range(2), range(2)):
        tester(i, j, I0=0).expect(0)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir)
        else:
            tester.compile_and_run(target, directory=_dir,
                                   simulator=simulator,
                                   magma_opts={"sv": True})


def test_call_interface_clock(target, simulator, caplog):
    ops = [operator.add, operator.sub, operator.mul, lambda x, y: y - x]
    tester = fault.Tester(SimpleALU, SimpleALU.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1

    for i in range(0, 4):
        tester.circuit.config_data = i
        tester.step(2)
        tester(3, 2).expect(ops[i](BitVector[16](3), BitVector[16](2)))
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        _dir = "build"
        if target == "verilator":
            tester.compile_and_run(target, directory=_dir,
                                   flags=["-Wno-unused"])
        else:
            tester.compile_and_run(target, directory=_dir,
                                   simulator=simulator,
                                   magma_opts={"sv": True})
    warning = "Number of arguments to __call__ did not match number of " \
              "circuit inputs"
    assert warning in caplog.messages
