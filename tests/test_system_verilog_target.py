import filecmp
import functools
import itertools
import os.path
import random
import shutil
import tempfile
import magma as m
import fault
import pytest
from .common import TestBasicClkCircuit, pytest_sim_params


def _with_random_seed(seed):

    def decorator(fn):

        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            state = random.getstate()
            random.seed(seed)
            ret = fn(*args, **kwargs)
            random.setstate(state)
            return ret

        return wrapped

    return decorator


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
        io.valid.undriven()

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
        verilog = "assign O = 4'dx;"

    tester = fault.Tester(X)
    tester.eval()
    tester.circuit.O.expect(fault.UnknownValue)
    tester.assert_(tester.peek(X.O) == fault.UnknownValue)
    tester.compile_and_run(target, simulator=simulator)
    with pytest.raises(AssertionError):
        # Expect is strict, so this should fail
        tester.circuit.O.expect(0)
        tester.compile_and_run(target, simulator=simulator)


def test_num_cycles_none():
    class Foo(m.Circuit):
        io = m.IO(valid=m.Out(m.Bit)) + m.ClockIO()
        io.valid.undriven()

    tester = fault.SynchronousTester(Foo, Foo.CLK)
    tester.wait_until_high(tester.circuit.valid)
    tester.compile_and_run(target="system-verilog",
                           simulator="xcelium", skip_run=True,
                           num_cycles=None)
    with open("build/Foo_cmd.tcl") as f:
        assert "run" == f.read().splitlines()[0]


def _test_packed_arrays_stimulate_by_element(tester, dut):
    NUM_POKES = 100
    for _ in range(NUM_POKES):
        i, j, k = map(random.randrange, (5, 12, 3))
        val = random.randint(0, (1 << 6) - 1)
        tester.poke(dut.I[i][j][k], val)
        tester.eval()
        tester.expect(dut.O[i][j][k], val)


def _test_packed_arrays_stimulate_bulk(tester, dut):
    NUM_POKES = 100
    for _ in range(NUM_POKES):
        i, j = map(random.randrange, (5, 12))
        val = [random.randint(0, (1 << 6) - 1) for _ in range(3)]
        tester.poke(dut.I[i][j], val)
        tester.eval()
        tester.expect(dut.O[i][j], val)


@_with_random_seed(0)
@pytest.mark.parametrize(
    "use_packed_arrays,stimulator",
    itertools.product(
        (False, True),
        (
            _test_packed_arrays_stimulate_by_element,
            _test_packed_arrays_stimulate_bulk,
        )
    )
)
def test_packed_arrays(use_packed_arrays, stimulator):
    name_ = f"test_system_verilog_target_packed_arrays_{use_packed_arrays}"
    name_ = f"{name_}_{stimulator.__name__}"

    class _Foo(m.Circuit):
        name = name_
        T = m.Array[5, m.Array[12, m.Array[3, m.Bits[6]]]]
        io = m.IO(I=m.In(T), O=m.Out(T))
        io.O @= io.I

    # skip_run = not shutil.which("vcs")
    # TODO: Enable run when MLIR is merged
    skip_run = True
    tester = fault.Tester(_Foo)
    stimulator(tester, _Foo)
    tester.compile_and_run(
        target="system-verilog",
        simulator="vcs",
        skip_compile=True,
        skip_run=skip_run,
        use_packed_arrays=use_packed_arrays,
    )
    assert filecmp.cmp(f"gold/{name_}_tb.sv", f"build/{name_}_tb.sv")
