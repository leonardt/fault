import tempfile
import fault
from fault import Tester
import shutil
import random
import pytest
from .common import (SimpleALU, TestNestedArraysCircuit,
                     TestDoubleNestedArraysCircuit, TestTupleCircuit,
                     AndCircuit, outlines, TestBasicCircuit)

TEST_START = '*** TEST START ***'


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None), ("python", None)]
        if shutil.which("irun"):
            targets.append(("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(("system-verilog", "vcs"))
        if shutil.which("iverilog"):
            targets.append(("system-verilog", "iverilog"))
        metafunc.parametrize("target,simulator", targets)


def run_test(target, simulator, tester, disp_type='on_error'):
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        kwargs = {}
        if target != "python":
            kwargs["directory"] = _dir
            kwargs["disp_type"] = disp_type
        if target == "verilator":
            kwargs["magma_opts"] = {"verilator_debug": True}
            kwargs["flags"] = ["-Wno-fatal"]
        if simulator is not None:
            kwargs["magma_opts"] = {"sv": True}
            kwargs["simulator"] = simulator
        tester.compile_and_run(target, **kwargs)


def test_tester_magma_internal_signals(target, simulator, capsys):
    circ = SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    tester.print(TEST_START + '\n')
    for i in range(0, 4):
        tester.circuit.config_data = i
        tester.step(2)
        tester.circuit.config_reg.Q.expect(i)
        signal = tester.circuit.config_reg.Q
        tester.circuit.config_reg.Q.expect(signal)
        tester.print("Q=%d\n", signal)
    run_test(target, simulator, tester, disp_type='realtime')
    messages = outlines(capsys)
    idx = messages.index(TEST_START) + 1
    actual = "\n".join(messages[idx:idx + 4])
    expected = """\
Q=0
Q=1
Q=2
Q=3\
"""
    assert expected == actual, "Print of internal register value did not work"


def test_tester_poke_internal_register(target, simulator, capsys):
    if target == "python":
        pytest.skip("Wrapped verilog not supported by Python simulator")
    circ = SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 0
    # Initialize
    tester.step(2)
    tester.print(TEST_START + '\n')
    for i in reversed(range(4)):
        tester.circuit.config_reg.conf_reg.value = i
        tester.step(2)
        tester.circuit.config_reg.conf_reg.O.expect(i)
        tester.print("O=%d\n", tester.circuit.config_reg.conf_reg.O)
    run_test(target, simulator, tester, disp_type='realtime')
    messages = outlines(capsys)
    idx = messages.index(TEST_START) + 1
    actual = "\n".join(messages[idx:idx + 4])
    expected = """\
O=3
O=2
O=1
O=0\
"""
    assert expected == actual, "Print of internal register value did not work"


def test_setattr_nested_arrays_by_element(target, simulator):
    circ = TestNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        tester.circuit.I[i] = val
        tester.eval()
        tester.circuit.O[i].expect(val)
    run_test(target, simulator, tester)


def test_setattr_nested_arrays_bulk(target, simulator):
    circ = TestNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
    tester.circuit.I = val
    tester.eval()
    tester.circuit.O.expect(val)
    run_test(target, simulator, tester)


def test_setattr_double_nested_arrays_by_element(target, simulator):
    circ = TestDoubleNestedArraysCircuit
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
    circ = TestDoubleNestedArraysCircuit
    tester = Tester(circ)
    expected = []
    val = [[random.randint(0, (1 << 4) - 1) for _ in range(3)]
           for _ in range(2)]
    tester.circuit.I = val
    tester.eval()
    tester.circuit.O.expect(val)
    run_test(target, simulator, tester)


def test_setattr_tuple(target, simulator):
    circ = TestTupleCircuit
    tester = Tester(circ)
    tester.circuit.I.a = 5
    tester.circuit.I.b = 11
    tester.eval()
    tester.circuit.O.a.expect(5)
    tester.circuit.O.b.expect(11)
    run_test(target, simulator, tester)


def test_setattr_x(target, simulator):
    if target == "verilator":
        pytest.skip("X not support with Verilator")
    if target == "python":
        pytest.skip("X not support with magma Python simulator")
    circ = AndCircuit
    tester = Tester(circ)
    # "0" & "1" -> "0"
    tester.circuit.I0 = 0
    tester.circuit.I1 = 1
    tester.eval()
    tester.circuit.O.expect(0)
    # "X" & "1" -> "X"
    tester.circuit.I0 = fault.UnknownValue
    tester.circuit.I1 = 1
    tester.eval()
    tester.circuit.O.expect(fault.UnknownValue)
    # "X" & "X" -> "X"
    tester.circuit.I0 = fault.UnknownValue
    tester.circuit.I1 = fault.UnknownValue
    tester.eval()
    tester.circuit.O.expect(fault.UnknownValue)
    run_test(target, simulator, tester)


def test_setattr_basic_fail(target, simulator, capsys):
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.circuit.I = 1
    tester.eval()
    tester.circuit.O.expect(0, msg=("MY_MESSAGE: got %x, expected 0!",
                                    tester.circuit.O))
    with pytest.raises(AssertionError) as e:
        run_test(target, simulator, tester)
    if target == "python":
        assert "MY_MESSAGE: got 1, expected 0!" in str(e)
    else:
        out, err = capsys.readouterr()
        assert "MY_MESSAGE: got 1, expected 0!" in out, out + err


def test_setattr_basic_fail2(target, simulator, capsys):
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.circuit.I = 1
    tester.eval()
    tester.circuit.O.expect(0, msg="my error message")
    with pytest.raises(AssertionError) as e:
        run_test(target, simulator, tester)
    if target == "python":
        assert "my error message" in str(e)
    else:
        out, err = capsys.readouterr()
        assert "my error message" in out, out + err


def test_set_invalid_port():
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    with pytest.raises(AttributeError):
        tester.circuit.not_a_port = 0
