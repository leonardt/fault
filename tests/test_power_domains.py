import magma as m
import mantle
import fault
from hwtypes import BitVector
import glob
import shutil

def test_power_domains():
    type_map = {"clk": m.In(m.Clock)}
    circ = m.DefineFromVerilogFile("./tests/build/Tile_PE.v",
                                   type_map=type_map, target_modules=["Tile_PE"])[0]
    tester = fault.PowerTester(circ, circ.clk)
    tester.add_power(circ.VDD)
    tester.add_ground(circ.VSS)
    tester.add_tri(circ.VDD_SW)

    tester.circuit.clk = 0
    tester.circuit.config_config_addr = 0 

    #======================================
    # TEST 1 - RESET TILE 
    # Check if tile is turned ON after reset 
    #======================================
    tester.circuit.reset = 1
    tester.step(2)
    tester.circuit.reset = 0
    tester.eval()
    tester.step(2)
    tester.circuit.VDD_SW.expect(1)  

    #====================================== 
    # TEST 2 - DISABLE PS REGISTER   
    # Check if power switch can be disabled 
    #====================================== 
    # Disable before enabling
    tester.circuit.tile_id = 0  
    tester.circuit.config_write = 1
    tester.circuit.config_read = 0
    tester.circuit.stall = 0
    tester.circuit.read_config_data_in = 0x0    
    tester.circuit.config_config_addr = 0x00080000
    tester.circuit.config_config_data = 0xFFFFFFF1
    tester.circuit.config_write = 1
    tester.eval()
    tester.step(2)
    tester.circuit.PowerDomainConfigReg_inst0.ps_en_out.expect(1) 
    
    #======================================
    # TEST 3 - ENABLE PS REGISTER
    # Check power switch register write
    #======================================
    # Disable before enabling
    tester.circuit.tile_id = 0
    tester.circuit.config_write = 1
    tester.circuit.config_read = 0
    tester.circuit.stall = 0
    tester.circuit.read_config_data_in = 0x0
    tester.circuit.config_config_addr = 0x00080000
    tester.circuit.config_config_data = 0xFFFFFFF1
    tester.circuit.config_write = 1
    tester.circuit.config_config_addr = 0x00080000
    tester.circuit.config_config_data = 0xFFFFFFF0
    tester.eval()
    tester.step(2)
    tester.circuit.VDD_SW.expect(1)
    tester.circuit.PowerDomainConfigReg_inst0.ps_en_out.expect(0)
    #======================================
    # RUN POINTWISE
    #======================================     
    # TEST 4 - VERIFY GLOBAL SIGNALS       
    # Check global signals are ON after tile is OFF      
    #======================================     
    tester.circuit.config_config_addr = 0x00080000
    tester.circuit.config_config_data = 0xFFFFFFF1
    tester.circuit.tile_id = 0
    tester.circuit.config_write = 1
    tester.circuit.config_read = 0
    tester.circuit.stall = 0
    tester.circuit.read_config_data_in = 0x0
    tester.eval()
    tester.step(2)
    tester.circuit.clk_out.expect(tester.circuit.clk)
    tester.circuit.reset_out.expect(tester.circuit.reset)
    tester.circuit.config_out_write.expect(tester.circuit.config_write)
    tester.circuit.config_out_read.expect(tester.circuit.config_read)
    tester.circuit.config_out_config_addr.expect(tester.circuit.config_config_addr)
    tester.circuit.config_out_config_data.expect(tester.circuit.config_config_data)
    tester.circuit.stall_out.expect(tester.circuit.stall)
    tester.circuit.read_config_data.expect(tester.circuit.read_config_data)  

    for cells in glob.glob("./tests/verilog/*.v"):
        shutil.copy(cells, "tests/build")
    tester.compile_and_run(target="system-verilog", simulator="ncsim",
                           directory="tests/build", skip_compile=True, include_verilog_libraries=["tcbn16ffcllbwp16p90_pwr.v", "tcbn16ffcllbwp16p90pm_pwr.v"], allow_redefinition=True)
