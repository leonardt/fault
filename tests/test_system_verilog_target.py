import os.path
import shutil
import tempfile
import fault
import pytest
from .common import TestBasicClkCircuit


def test_vcs_waves():
    if not shutil.which("vcs"):
        pytest.skip("Skipping vcs waveform test because vcs is not available")
    circ = TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.circuit.I = 0
    tester.step(2)
    tester.circuit.I = 1
    tester.step(2)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator="vcs",
                               directory=_dir, vcs_waveform_file="waves.vpd")
        assert os.path.exists(os.path.join(_dir, "waves.vpd"))

