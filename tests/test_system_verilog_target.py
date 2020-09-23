import os.path
import shutil
import tempfile
import fault
import pytest
from .common import TestBasicClkCircuit


@pytest.mark.parametrize("simulator,waveform_type", [("ncsim", "vcd"),
                                                     ("xcelium", "vcd"),
                                                     ("vcs", "vpd"),
                                                     ("vcs", "fsdb")])
@pytest.mark.parametrize("use_sva", [True, False])
def test_waves(simulator, waveform_type, use_sva):
    if simulator == 'vcs' and not shutil.which("vcs"):
        pytest.skip("Skipping vcs waveform test because vcs is not available")
    if simulator == 'ncsim' and not shutil.which("irun"):
        pytest.skip("Skipping ncsim waveform test because ncsim is not "
                    "available")
    if simulator == 'xcelium' and not shutil.which("xrun"):
        pytest.skip("Skipping xcelium waveform test because xrun is not "
                    "available")
    circ = TestBasicClkCircuit
    tester = fault.Tester(circ, circ.CLK)
    tester.circuit.I = 0
    tester.step(2)
    tester.circuit.I = 1
    tester.step(2)
    flags = []
    if waveform_type == "fsdb":
        # Note this will only work on kiwi/buildkite env, users should set
        # their specific link flags
        verdi_home = os.environ["VERDIHOME"]
        flags += ['-P',
                  f' {verdi_home}/share/PLI/vcs_latest/LINUX64/novas.tab',
                  f' {verdi_home}/share/PLI/vcs_latest/LINUX64/pli.a']
    # Test default
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, use_sva=use_sva,
                               waveform_type=waveform_type,
                               dump_waveforms=True, flags=flags)
        assert os.path.exists(os.path.join(_dir,
                                           f"waveforms.{waveform_type}"))

    # Test custom
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir,
                               waveform_file=f"waves.{waveform_type}",
                               use_sva=use_sva, waveform_type=waveform_type,
                               dump_waveforms=True, flags=flags)
        assert os.path.exists(os.path.join(_dir, f"waves.{waveform_type}"))

    # Test off
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, dump_waveforms=False,
                               use_sva=use_sva, waveform_type=waveform_type)
        assert not os.path.exists(os.path.join(_dir,
                                               f"waveforms.{waveform_type}"))
