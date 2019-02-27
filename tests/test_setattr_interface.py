import common
import tempfile
from fault import Tester
import shutil
import random
from bit_vector import BitVector
import operator
import delegator


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if shutil.which("irun"):
            targets.append(("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(("system-verilog", "vcs"))
        metafunc.parametrize("target,simulator", targets)


def run_test(target, simulator, tester):
    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "directory": _dir,
            "magma_opts": {"verilator_debug": True}
        }
        if target == "verilator":
            kwargs["flags"] = ["-Wno-fatal"]
        if simulator is not None:
            kwargs["simulator"] = simulator
        tester.compile_and_run(target, **kwargs)


def test_tester_magma_internal_signals(target, simulator):
    circ = common.SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    for i in range(0, 4):
        tester.circuit.config_data = i
        tester.step(2)
        tester.circuit.config_reg.Q.expect(i)
        signal = tester.circuit.config_reg.Q
        tester.circuit.config_reg.Q.expect(signal)
    run_test(target, simulator, tester)


def test_tester_poke_internal_register(target, simulator):
    circ = common.SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.CLK = 0
    # Initialize
    tester.step(2)
    for i in reversed(range(4)):
        tester.circuit.config_reg.conf_reg.value = i
        tester.step(2)
        tester.circuit.config_reg.conf_reg.O.expect(i)
    run_test(target, simulator, tester)


def test_setattr_nested_arrays_by_element(target, simulator):
    circ = common.TestNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.circuit.I[i] = val
        tester.eval()
        tester.circuit.O[i].expect(val)
    run_test(target, simulator, tester)


def test_setattr_nested_arrays_bulk(target, simulator):
    circ = common.TestNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
    tester.circuit.I = val
    tester.eval()
    tester.circuit.O.expect(val)
    run_test(target, simulator, tester)


def test_setattr_double_nested_arrays_by_element(target, simulator):
    circ = common.TestDoubleNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    for j in range(2):
        for i in range(3):
            val = random.randint(0, (1 << 4) - 1)
            tester.circuit.I[j][i] = val
            tester.eval()
            tester.circuit.O[j][i].expect(val)
    run_test(target, simulator, tester)


def test_setattr_double_nested_arrays_bulk(target, simulator):
    circ = common.TestDoubleNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3) for _ in range(2)]
    tester.circuit.I = val
    tester.eval()
    tester.circuit.O.expect(val)
    run_test(target, simulator, tester)


def test_setattr_tuple(target, simulator):
    circ = common.TestTupleCircuit
    tester = Tester(circ)
    tester.circuit.I.a = 5
    tester.circuit.I.b = 11
    tester.eval()
    tester.circuit.O.a.expect(5)
    tester.circuit.O.b.expect(11)
    run_test(target, simulator, tester)


# def test_tester_coverage(target, simulator):
def test_tester_coverage():
    target = "verilator"
    simulator = None
    circ = common.SimpleALU2

    tester = Tester(circ, circ.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    for i in range(0, 3):
        tester.circuit.config_data = i
        tester.step(2)
        tester.circuit.config_reg.Q.expect(i)
        signal = tester.circuit.config_reg.Q
        tester.circuit.config_reg.Q.expect(signal)
        for j in range(0, 4):
            for k in range(0, 4):
                a = BitVector(j, 2)
                b = BitVector(k, 2)
                tester.circuit.a = a
                tester.circuit.b = b
                tester.eval()
                tester.circuit.c.expect([operator.add, operator.sub,
                                         operator.mul, operator.sub][i](a, b))
    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "directory": _dir,
            "magma_opts": {"verilator_debug": True}
        }
        if target == "verilator":
            kwargs["flags"] = ["-Wno-fatal"]
        if simulator is not None:
            kwargs["simulator"] = simulator
        tester.compile_and_run(target, coverage="toggle", **kwargs)
        import subprocess
        result = delegator.run(
            f"verilator_coverage logs/{circ.name}.dat -annotate logs",
            cwd=_dir)
        assert result.out.splitlines()[0] == "Total coverage (71/130) 54.00%"
