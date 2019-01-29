import common
from fault import Tester


def test_tester_magma_internal_signals():
    circ = common.SimpleALU

    tester = Tester(circ, circ.CLK)
    tester.circuit.config_en = 1
    for i in range(0, 4):
        tester.circuit.config_data = 1
        tester.step(2)
        tester.circuit.config_reg.Q.expect(i)
        signal = tester.circuit.config_reg.Q
        tester.circuit.config_reg.Q.expect(signal)
    with tempfile.TemporaryDirectory() as _dir:
        tester.compile_and_run(verilator, directory=_dir, flags=["-Wno-fatal"])
