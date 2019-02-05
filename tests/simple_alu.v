module ConfigReg(input [1:0] D, output reg [1:0] Q /*verilator public*/, input CLK, input EN);
always @(posedge CLK) begin
    if (EN) Q <= D;
end
endmodule

module SimpleALU(input [15:0] a, input [15:0] b, output reg [15:0] c, input [1:0] config_data, input config_en, input CLK);

wire [1:0] opcode/*verilator public*/;
ConfigReg config_reg(config_data, opcode, CLK, config_en);


always @(*) begin
    case (opcode)
        0: c = a + b;
        1: c = a - b;
        2: c = a * b;
        3: c = a / b;
    endcase
end
endmodule
