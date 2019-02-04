import common
import tempfile
from fault import Tester
import shutil


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if shutil.which("irun"):
            targets.append(("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(("system-verilog", "vcs"))
        metafunc.parametrize("target,simulator", targets)


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
    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "directory": "build",
            "magma_opts": {"verilator_debug": True}
        }
        if target == "verilator":
            kwargs["flags"] = ["-Wno-fatal"]
        if simulator is not None:
            kwargs["simulator"] = simulator
        tester.compile_and_run(target, **kwargs)


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
    with tempfile.TemporaryDirectory() as _dir:
        kwargs = {
            "directory": "build",
            "magma_opts": {"verilator_debug": True}
        }
        if target == "verilator":
            kwargs["flags"] = ["-Wno-fatal"]
        if simulator is not None:
            kwargs["simulator"] = simulator
        tester.compile_and_run(target, **kwargs)
