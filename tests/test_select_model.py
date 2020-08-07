"""
Tests support for selecting different implementations of a DUT (or
subcomponents of a DUT)
"""
import magma as m
import mantle
import fault
import hwtypes as ht
import os
import tempfile


def test_top():
    # First, we define an interface generator for an N-bit adder
    def DeclareAdder(N):
        """
        Generates the interface for an N-bit adder
        """
        T = m.UInt[N]

        class Adder(m.Circuit):
            io = m.IO(I0=m.In(T), I1=m.In(T), CIN=m.In(m.Bit),
                      O=m.Out(T), COUT=m.Out(m.Bit))
        return Adder

    # Define generators for two different implementations of an adder, one is
    # structural, one is behavioral
    def DefineAdderStructural(N):
        """
        Generate a structural adder
        """
        AdderNDecl = DeclareAdder(N)

        class Adder(AdderNDecl):
            io = AdderNDecl.io
            adders = [mantle.FullAdder() for _ in range(N)]
            adders = m.fold(adders, foldargs={"CIN": "COUT"})
            COUT, O = adders(I0=io.I0, I1=io.I1, CIN=io.CIN)
            m.wire(O, io.O)
            m.wire(COUT, io.COUT)
        return Adder

    def DefineAdderBehavioral(N):
        """
        Generate a behavioral adder
        """
        AdderNDecl = DeclareAdder(N)

        class Adder(AdderNDecl):
            io = AdderNDecl.io
            # Swap this line with the commented code in the following line
            # to induce a failure in the behavioral test
            O = io.I0.zext(1) + io.I1.zext(1) + m.bits(io.CIN, 1).zext(N)
            # O = io.I0.zext(1) - io.I1.zext(1) - m.bits(io.CIN, 1).zext(N)
            m.wire(O[:N], io.O)
            m.wire(O[-1], io.COUT)
        return Adder

    # Define a simple DUT that instances an adder and passes through the
    # wires
    T = m.Bits[4]

    class DUT(m.Circuit):
        io = m.IO(I0=m.In(T), I1=m.In(T), CIN=m.In(m.Bit),
                  O=m.Out(T), COUT=m.Out(m.Bit))

        # Instance declaration of adder, definition will be selected
        # later
        Adder4 = DeclareAdder(4)
        adder0 = Adder4(name="adder0")
        adder1 = Adder4(name="adder1")
        # Random logic with the two adders
        O, COUT = adder0(io.I0, io.I1, io.CIN)
        O, COUT = adder1(O, O, COUT)
        io.O <= O
        io.COUT <= COUT

    # Generic adder test bench using DUT
    tester = fault.Tester(DUT)
    tester.circuit.adder0.set_definition(DefineAdderBehavioral(4))
    tester.circuit.adder1.set_definition(DefineAdderStructural(4))
    for i in range(10):
        tester.circuit.I0 = I0 = ht.BitVector.random(4)
        tester.circuit.I1 = I1 = ht.BitVector.random(4)
        tester.circuit.CIN = CIN = ht.BitVector.random(1)[0]
        tester.eval()
        O = I0.zext(1) + I1.zext(1) + ht.BitVector[5](CIN)
        O, COUT = O[:4], O[-1]
        O = O.zext(1) + O.zext(1) + ht.BitVector[5](COUT)
        O, COUT = O[:4], O[-1]
        tester.circuit.O.expect(O)
        tester.circuit.COUT.expect(COUT)

    with tempfile.TemporaryDirectory() as directory:
        tester.compile_and_run(target="verilator", directory=directory)
        # Assert that the generated verilog generates two different adders
        with open(os.path.join(directory, "DUT.v"), "r") as f:
            assert f.read() == """\
module coreir_orr #(
    parameter width = 1
) (
    input [width-1:0] in,
    output out
);
  assign out = |in;
endmodule

module coreir_add #(
    parameter width = 1
) (
    input [width-1:0] in0,
    input [width-1:0] in1,
    output [width-1:0] out
);
  assign out = in0 + in1;
endmodule

module corebit_xor (
    input in0,
    input in1,
    output out
);
  assign out = in0 ^ in1;
endmodule

module fold_xor3None (
    input I0,
    input I1,
    input I2,
    output O
);
wire xor_inst0_in0;
wire xor_inst0_in1;
wire xor_inst0_out;
wire xor_inst1_in0;
wire xor_inst1_in1;
wire xor_inst1_out;
assign xor_inst0_in0 = I0;
assign xor_inst0_in1 = I1;
corebit_xor xor_inst0 (
    .in0(xor_inst0_in0),
    .in1(xor_inst0_in1),
    .out(xor_inst0_out)
);
assign xor_inst1_in0 = xor_inst0_out;
assign xor_inst1_in1 = I2;
corebit_xor xor_inst1 (
    .in0(xor_inst1_in0),
    .in1(xor_inst1_in1),
    .out(xor_inst1_out)
);
assign O = xor_inst1_out;
endmodule

module corebit_const #(
    parameter value = 1
) (
    output out
);
  assign out = value;
endmodule

module corebit_and (
    input in0,
    input in1,
    output out
);
  assign out = in0 & in1;
endmodule

module Or3xNone (
    input I0,
    input I1,
    input I2,
    output O
);
wire [2:0] orr_inst0_in;
wire orr_inst0_out;
assign orr_inst0_in = {I2,I1,I0};
coreir_orr #(
    .width(3)
) orr_inst0 (
    .in(orr_inst0_in),
    .out(orr_inst0_out)
);
assign O = orr_inst0_out;
endmodule

module FullAdder (
    input I0,
    input I1,
    input CIN,
    output O,
    output COUT
);
wire Or3xNone_inst0_I0;
wire Or3xNone_inst0_I1;
wire Or3xNone_inst0_I2;
wire Or3xNone_inst0_O;
wire and_inst0_in0;
wire and_inst0_in1;
wire and_inst0_out;
wire and_inst1_in0;
wire and_inst1_in1;
wire and_inst1_out;
wire and_inst2_in0;
wire and_inst2_in1;
wire and_inst2_out;
wire fold_xor3None_inst0_I0;
wire fold_xor3None_inst0_I1;
wire fold_xor3None_inst0_I2;
wire fold_xor3None_inst0_O;
assign Or3xNone_inst0_I0 = and_inst0_out;
assign Or3xNone_inst0_I1 = and_inst1_out;
assign Or3xNone_inst0_I2 = and_inst2_out;
Or3xNone Or3xNone_inst0 (
    .I0(Or3xNone_inst0_I0),
    .I1(Or3xNone_inst0_I1),
    .I2(Or3xNone_inst0_I2),
    .O(Or3xNone_inst0_O)
);
assign and_inst0_in0 = I0;
assign and_inst0_in1 = I1;
corebit_and and_inst0 (
    .in0(and_inst0_in0),
    .in1(and_inst0_in1),
    .out(and_inst0_out)
);
assign and_inst1_in0 = I1;
assign and_inst1_in1 = CIN;
corebit_and and_inst1 (
    .in0(and_inst1_in0),
    .in1(and_inst1_in1),
    .out(and_inst1_out)
);
assign and_inst2_in0 = I0;
assign and_inst2_in1 = CIN;
corebit_and and_inst2 (
    .in0(and_inst2_in0),
    .in1(and_inst2_in1),
    .out(and_inst2_out)
);
assign fold_xor3None_inst0_I0 = I0;
assign fold_xor3None_inst0_I1 = I1;
assign fold_xor3None_inst0_I2 = CIN;
fold_xor3None fold_xor3None_inst0 (
    .I0(fold_xor3None_inst0_I0),
    .I1(fold_xor3None_inst0_I1),
    .I2(fold_xor3None_inst0_I2),
    .O(fold_xor3None_inst0_O)
);
assign O = fold_xor3None_inst0_O;
assign COUT = Or3xNone_inst0_O;
endmodule

module Adder_unq1 (
    input [3:0] I0,
    input [3:0] I1,
    input CIN,
    output [3:0] O,
    output COUT
);
wire FullAdder_inst0_I0;
wire FullAdder_inst0_I1;
wire FullAdder_inst0_CIN;
wire FullAdder_inst0_O;
wire FullAdder_inst0_COUT;
wire FullAdder_inst1_I0;
wire FullAdder_inst1_I1;
wire FullAdder_inst1_CIN;
wire FullAdder_inst1_O;
wire FullAdder_inst1_COUT;
wire FullAdder_inst2_I0;
wire FullAdder_inst2_I1;
wire FullAdder_inst2_CIN;
wire FullAdder_inst2_O;
wire FullAdder_inst2_COUT;
wire FullAdder_inst3_I0;
wire FullAdder_inst3_I1;
wire FullAdder_inst3_CIN;
wire FullAdder_inst3_O;
wire FullAdder_inst3_COUT;
assign FullAdder_inst0_I0 = I0[0];
assign FullAdder_inst0_I1 = I1[0];
assign FullAdder_inst0_CIN = CIN;
FullAdder FullAdder_inst0 (
    .I0(FullAdder_inst0_I0),
    .I1(FullAdder_inst0_I1),
    .CIN(FullAdder_inst0_CIN),
    .O(FullAdder_inst0_O),
    .COUT(FullAdder_inst0_COUT)
);
assign FullAdder_inst1_I0 = I0[1];
assign FullAdder_inst1_I1 = I1[1];
assign FullAdder_inst1_CIN = FullAdder_inst0_COUT;
FullAdder FullAdder_inst1 (
    .I0(FullAdder_inst1_I0),
    .I1(FullAdder_inst1_I1),
    .CIN(FullAdder_inst1_CIN),
    .O(FullAdder_inst1_O),
    .COUT(FullAdder_inst1_COUT)
);
assign FullAdder_inst2_I0 = I0[2];
assign FullAdder_inst2_I1 = I1[2];
assign FullAdder_inst2_CIN = FullAdder_inst1_COUT;
FullAdder FullAdder_inst2 (
    .I0(FullAdder_inst2_I0),
    .I1(FullAdder_inst2_I1),
    .CIN(FullAdder_inst2_CIN),
    .O(FullAdder_inst2_O),
    .COUT(FullAdder_inst2_COUT)
);
assign FullAdder_inst3_I0 = I0[3];
assign FullAdder_inst3_I1 = I1[3];
assign FullAdder_inst3_CIN = FullAdder_inst2_COUT;
FullAdder FullAdder_inst3 (
    .I0(FullAdder_inst3_I0),
    .I1(FullAdder_inst3_I1),
    .CIN(FullAdder_inst3_CIN),
    .O(FullAdder_inst3_O),
    .COUT(FullAdder_inst3_COUT)
);
assign O = {FullAdder_inst3_O,FullAdder_inst2_O,FullAdder_inst1_O,FullAdder_inst0_O};
assign COUT = FullAdder_inst3_COUT;
endmodule

module Adder (
    input [3:0] I0,
    input [3:0] I1,
    input CIN,
    output [3:0] O,
    output COUT
);
wire bit_const_0_None_out;
wire [4:0] magma_Bits_5_add_inst0_in0;
wire [4:0] magma_Bits_5_add_inst0_in1;
wire [4:0] magma_Bits_5_add_inst0_out;
wire [4:0] magma_Bits_5_add_inst1_in0;
wire [4:0] magma_Bits_5_add_inst1_in1;
wire [4:0] magma_Bits_5_add_inst1_out;
corebit_const #(
    .value(1'b0)
) bit_const_0_None (
    .out(bit_const_0_None_out)
);
assign magma_Bits_5_add_inst0_in0 = {bit_const_0_None_out,I0[3:0]};
assign magma_Bits_5_add_inst0_in1 = {bit_const_0_None_out,I1[3:0]};
coreir_add #(
    .width(5)
) magma_Bits_5_add_inst0 (
    .in0(magma_Bits_5_add_inst0_in0),
    .in1(magma_Bits_5_add_inst0_in1),
    .out(magma_Bits_5_add_inst0_out)
);
assign magma_Bits_5_add_inst1_in0 = magma_Bits_5_add_inst0_out;
assign magma_Bits_5_add_inst1_in1 = {bit_const_0_None_out,bit_const_0_None_out,bit_const_0_None_out,bit_const_0_None_out,CIN};
coreir_add #(
    .width(5)
) magma_Bits_5_add_inst1 (
    .in0(magma_Bits_5_add_inst1_in0),
    .in1(magma_Bits_5_add_inst1_in1),
    .out(magma_Bits_5_add_inst1_out)
);
assign O = magma_Bits_5_add_inst1_out[3:0];
assign COUT = magma_Bits_5_add_inst1_out[4];
endmodule

module DUT (
    input [3:0] I0,
    input [3:0] I1,
    input CIN,
    output [3:0] O,
    output COUT
);
wire [3:0] adder0_I0;
wire [3:0] adder0_I1;
wire adder0_CIN;
wire [3:0] adder0_O;
wire adder0_COUT;
wire [3:0] adder1_I0;
wire [3:0] adder1_I1;
wire adder1_CIN;
wire [3:0] adder1_O;
wire adder1_COUT;
assign adder0_I0 = I0;
assign adder0_I1 = I1;
assign adder0_CIN = CIN;
Adder adder0 (
    .I0(adder0_I0),
    .I1(adder0_I1),
    .CIN(adder0_CIN),
    .O(adder0_O),
    .COUT(adder0_COUT)
);
assign adder1_I0 = adder0_O;
assign adder1_I1 = adder0_O;
assign adder1_CIN = adder0_COUT;
Adder_unq1 adder1 (
    .I0(adder1_I0),
    .I1(adder1_I1),
    .CIN(adder1_CIN),
    .O(adder1_O),
    .COUT(adder1_COUT)
);
assign O = adder1_O;
assign COUT = adder1_COUT;
endmodule

"""  # noqa
