import os.path
import shutil
import tempfile
import magma as m
import fault
import pytest
from .common import TestBasicClkCircuit, pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


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
    kwargs = {}
    if waveform_type == "fsdb":
        # Note this will only work on kiwi/buildkite env, users should set
        # their specific link flags
        verdi_home = os.environ["VERDI_HOME"]
        flags += ['-P',
                  f' {verdi_home}/share/PLI/VCS/LINUX64/novas.tab',
                  f' {verdi_home}/share/PLI/VCS/LINUX64/pli.a']
        kwargs["fsdb_dumpvars_args"] = '0, "dut"'
    # Test default
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, use_sva=use_sva,
                               waveform_type=waveform_type,
                               dump_waveforms=True, flags=flags, **kwargs)
        assert os.path.exists(os.path.join(_dir,
                                           f"waveforms.{waveform_type}"))

    # Test custom
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir,
                               waveform_file=f"waves.{waveform_type}",
                               use_sva=use_sva, waveform_type=waveform_type,
                               dump_waveforms=True, flags=flags, **kwargs)
        assert os.path.exists(os.path.join(_dir, f"waves.{waveform_type}"))

    # Test off
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        tester.compile_and_run(target="system-verilog", simulator=simulator,
                               directory=_dir, dump_waveforms=False,
                               use_sva=use_sva, waveform_type=waveform_type,
                               **kwargs)
        assert not os.path.exists(os.path.join(_dir,
                                               f"waveforms.{waveform_type}"))


def test_wait_until_sv():
    class Foo(m.Circuit):
        io = m.IO(valid=m.Out(m.Bit)) + m.ClockIO()

    tester = fault.SynchronousTester(Foo, Foo.CLK)
    tester.wait_until_high(tester.circuit.valid)
    tester.compile_and_run(target="system-verilog",
                           simulator="iverilog", skip_run=True)
    with open("build/Foo_tb.sv") as f:
        # Should not be missing semicolon after wait
        assert "#5;" in f.read()


def test_unknown_value(target, simulator):
    if target == "verilator":
        pytest.skip("verilator does not support x")

    class X(m.Circuit):
        """
        Stub circuit to generate x
        """
        io = m.IO(O=m.Out(m.Bits[4]))
        verilog = "assign O = 'x;"

    tester = fault.Tester(X)
    tester.eval()
    tester.circuit.O.expect(fault.UnknownValue)
    tester.compile_and_run(target, simulator=simulator)
    with pytest.raises(AssertionError):
        # Expect is strict, so this should fail
        tester.circuit.O.expect(0)
        tester.compile_and_run(target, simulator=simulator)
