// From https://raw.githubusercontent.com/YosysHQ/yosys/master/techlibs/ice40/cells_sim.v
`define SB_DFF_REG reg Q = 0

module SB_DFF (output `SB_DFF_REG, input C, D);
	always @(posedge C)
		Q <= D;
endmodule
