module simple_alu_pd(input [15:0] a, input [15:0] b, output [15:0] c,
		     input [15:0] config_addr,
		     input [15:0] config_data, input [15:0] config_en,
		     input CLK, input VDD_HIGH, input VSS,
		     input VDD_HIGH_TOP_VIRTUAL, output stall_out,
		     output reset);

   // stub to test support for reading in modules with supply1,
   // supply0, and tri types
endmodule
