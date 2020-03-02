import fault
from hwtypes import BitVector
from fault.functional_tester import FunctionalTester
import magma as m
import mantle
import tempfile
import pytest


@pytest.mark.skip("Blocked by https://github.com/rdaly525/coreir/issues/627")
def test_configuration():
    class ConfigurationTester(FunctionalTester):
        def configure(self, addr, data):
            self.poke(self.clock, 0)
            self.poke(self.circuit.config_addr, addr)
            self.poke(self.circuit.config_data, data)
            self.poke(self.circuit.config_en, 1)
            self.step()
            self.functional_model.configure(addr, data)
            self.eval()

    class Configurable(m.Circuit):
        io = m.IO(config_addr=m.In(m.Bits[32]), config_data=m.In(m.Bits[32]),
                  config_en=m.In(m.Enable), O=m.Out(m.Bits[32])
                  ) + m.ClockIO()

        reg = mantle.Register(32, has_ce=True)

        reg(io.config_data,
            CE=(io.config_addr == m.bits(1, 32)) & m.bit(io.config_en))
        m.wire(reg.O, io.O)

    class ConfigurableModel:
        def __init__(self):
            self.O = fault.UnknownValue

        def configure(self, addr, data):
            if addr == BitVector(1, 32):
                self.O = data

    model = ConfigurableModel()
    tester = ConfigurationTester(Configurable, Configurable.CLK,
                                 model)
    model.O = fault.AnyValue
    tester.configure(0, 12)
    tester.configure(1, 32)
    tester.configure(0, 23)
    tester.configure(1, 41)
    with tempfile.TemporaryDirectory() as tmp_dir:
        m.compile(f"{tmp_dir}/Configurable", Configurable,
                  output="coreir-verilog")
        tester.compile_and_run(directory=tmp_dir, target="verilator",
                               flags=["-Wno-fatal"], skip_compile=True,
                               circuit_name="Configurable")
