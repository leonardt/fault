import os.path
import shutil
import tempfile
import fault
import pytest
from .common import TestBasicClkCircuit


@pytest.mark.parametrize("simulator", ["ncsim", "vcs"])
def test_waves(simulator):
    if simulator == 'vcs' and not shutil.which("vcs"):
        pytest.skip("Skipping vcs waveform test because vcs is not available")
    if simulator == 'ncsim' and not shutil.which("irun"):
        pytest.skip("Skipping ncsim waveform test because ncsim is not "
                    "available")
    suffix = "vcd" if simulator == "ncsim" else "vpd"
    circ = TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.circuit.I = 0
    tester.step(2)
    tester.circuit.I = 1
    tester.step(2)
    # Test default
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        _dir = "build"
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir)
        assert os.path.exists(os.path.join(_dir, f"waveforms.{suffix}"))

    # Test custom
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, waveform_file=f"waves.{suffix}")
        assert os.path.exists(os.path.join(_dir, f"waves.{suffix}"))

    # Test off
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, dump_waveforms=False)
        assert not os.path.exists(os.path.join(_dir, f"waveforms.{suffix}"))
