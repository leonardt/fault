import magma as m
import mantle
import fault
from hwtypes import BitVector
import pytest
import shutil


@pytest.mark.skipif(not shutil.which("irun"), reason="irun not available")
def test_simple_alu_pd():
    type_map = {"CLK": m.In(m.Clock)}
    circ = m.define_from_verilog_file("tests/verilog/simple_alu_pd.sv",
                                      type_map=type_map)[0]
    tester = fault.PowerTester(circ, circ.CLK)
    tester.add_power(circ.VDD_HIGH)
    tester.add_ground(circ.VSS)
    tester.add_tri(circ.VDD_HIGH_TOP_VIRTUAL)

    tester.circuit.CLK = 0

    # Enable the power switch
    tester.circuit.config_addr = 0x00080000
    tester.circuit.config_data = 0xFFFFFFF0
    tester.circuit.config_en = 1
    tester.step(2)
    tester.circuit.config_en = 0

    # rest of test...
    a, b = BitVector.random(16), BitVector.random(16)
    tester.circuit.a = a
    tester.circuit.b = b
    tester.circuit.c.expect(a + b)

    # Disable the power switch
    tester.circuit.config_addr = 0x00080000
    tester.circuit.config_data = 0xFFFFFFF0
    tester.circuit.config_en = 1
    tester.step(2)
    tester.circuit.config_en = 0
    # Stall global signal should be on when tile is off
    tester.circuit.stall_out.expect(1)
    # reset signal should be on when tile is off
    tester.circuit.reset.expect(1)

    # Enable the power switch
    tester.circuit.config_addr = 0x00080000
    tester.circuit.config_data = 0xFFFFFFF0
    tester.circuit.config_en = 1
    tester.step(2)
    tester.circuit.config_en = 0

    # rest of test...
    a, b = BitVector.random(16), BitVector.random(16)
    tester.circuit.a = a
    tester.circuit.b = b
    tester.circuit.c.expect(a + b)

    try:
        tester.compile_and_run(target="system-verilog", simulator="ncsim",
                               directory="tests/build", skip_compile=True)
    except AssertionError:
        # Won't run because we don't have concrete DUT or ncsim, but we check
        # that the output has the right types for the special ports
        with open("tests/build/simple_alu_pd_tb.sv", "r") as f:
            for line in f.read().splitlines():
                if "VDD_HIGH_TOP_VIRTUAL;" in line:
                    assert line.lstrip().rstrip() == \
                        "tri VDD_HIGH_TOP_VIRTUAL;"
                elif "VDD_HIGH;" in line:
                    assert line.lstrip().rstrip() == "supply1 VDD_HIGH;"
                elif "VSS;" in line:
                    assert line.lstrip().rstrip() == "supply0 VSS;"
