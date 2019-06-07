import magma as m

SimpleALU = m.DefineFromVerilog("""\
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
""", type_map={"CLK": m.In(m.Clock)}, target_modules=["SimpleALU"])[0]

circ = m.DefineCircuit("top",
                       "a", m.In(m.Bits[16]),
                       "b", m.In(m.Bits[16]),
                       "c", m.Out(m.Bits[16]),
                       "config_data", m.In(m.Bits[2]),
                       "config_en", m.In(m.Bit),
                       "CLK", m.In(m.Clock))
simple_alu = SimpleALU()
m.wire(simple_alu.a, circ.a)
m.wire(simple_alu.b, circ.b)
m.wire(simple_alu.c, circ.c)
m.wire(simple_alu.config_data, circ.config_data)
m.wire(simple_alu.config_en, circ.config_en)
m.wire(simple_alu.CLK, circ.CLK)
m.EndDefine()

m.compile("tmp", circ, output="coreir-verilog")
