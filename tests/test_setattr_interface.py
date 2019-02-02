import common
import tempfile
from fault import Tester


def test_tester_magma_internal_signals():
    circ = common.SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.config_en = 1
    for i in range(0, 4):
        tester.circuit.config_data = i
        tester.step(2)
        tester.circuit.config_reg.Q.expect(i)
        signal = tester.circuit.config_reg.Q
        tester.circuit.config_reg.Q.expect(signal)
    with tempfile.TemporaryDirectory() as _dir:
        tester.compile_and_run("verilator", directory=_dir,
                               flags=["-Wno-fatal"],
                               magma_opts={"verilator_debug": True})


def test_tester_poke_internal_register():
    circ = common.SimpleALU

    tester = Tester(circ, circ.CLK)
    # Initialize
    tester.step(2)
    for i in reversed(range(4)):
        tester.circuit.config_reg.conf_reg.value = i
        tester.step(2)
        tester.circuit.config_reg.conf_reg.O.expect(i)
    with tempfile.TemporaryDirectory() as _dir:
        _dir = "build"
        tester.compile_and_run("verilator", directory=_dir,
                               flags=["-Wno-fatal", "--trace"],
                               magma_opts={"verilator_debug": True})
