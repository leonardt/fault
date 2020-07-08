import tempfile
import os
from pprint import PrettyPrinter

from vcdvcd import VCDVCD

import fault as f
from ..common import SimpleALU


def test_init_clock():
    tester = f.Tester(SimpleALU, SimpleALU.CLK)
    tester.circuit.a = 1
    tester.circuit.b = 2
    tester.circuit.config_data = 0
    tester.circuit.config_en = 0
    tester.step(2)
    tester.circuit.c.expect(3)
    with tempfile.TemporaryDirectory() as tempdir:
        tester.compile_and_run("verilator", flags=["--trace", "-Wno-fatal"],
                               directory=tempdir)
        vcd_file = os.path.join(tempdir, "logs", "SimpleALU.vcd")
        vcd = VCDVCD(vcd_file, signals=["TOP.CLK"])
        # One elem dict, we can grab the first element
        tvs = next(iter(vcd.get_data().values()))["tv"]
        assert tvs == [(0, '0'), (5, '1'), (10, '0')]

        tester.compile_and_run("system-verilog", simulator="iverilog",
                               directory=tempdir)
        vcd_file = os.path.join(tempdir, "waveforms.vcd")
        vcd = VCDVCD(vcd_file, signals=["SimpleALU_tb.dut.CLK"])
        # One elem dict, we can grab the first element
        tvs = next(iter(vcd.get_data().values()))["tv"]
        assert tvs == [(0, '0'), (5, '1'), (10, '0')]