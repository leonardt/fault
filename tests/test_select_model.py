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
            IO = ["I0", m.In(T), "I1", m.In(T), "CIN", m.In(m.Bit),
                  "O", m.Out(T), "COUT", m.Out(m.Bit)]
        return Adder

    # Define generators for two different implementations of an adder, one is
    # structural, one is behavioral
    def DefineAdderStructural(N):
        """
        Generate a structural adder
        """
        class Adder(DeclareAdder(N)):
            @classmethod
            def definition(io):
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
        class Adder(DeclareAdder(N)):
            @classmethod
            def definition(io):
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
        IO = ["I0", m.In(T), "I1", m.In(T), "CIN", m.In(m.Bit),
              "O", m.Out(T), "COUT", m.Out(m.Bit)]

        @classmethod
        def definition(io):
            # Instance declaration of adder, definition will be selected
            # later
            Adder4 = DeclareAdder(4)
            adder0 = Adder4(name="adder0")
            adder1 = Adder4(name="adder1")
            # Random logic with the two adders
            O, COUT = adder0(io)
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
module coreir_orr #(parameter width = 1) (input [width-1:0] in, output out);
  assign out = |in;
endmodule

module coreir_add #(parameter width = 1) (input [width-1:0] in0, input [width-1:0] in1, output [width-1:0] out);
  assign out = in0 + in1;
endmodule

module corebit_xor (input in0, input in1, output out);
  assign out = in0 ^ in1;
endmodule

module fold_xor3None (input I0, input I1, input I2, output O);
wire xor_inst0_out;
wire xor_inst1_out;
corebit_xor xor_inst0(.in0(I0), .in1(I1), .out(xor_inst0_out));
corebit_xor xor_inst1(.in0(xor_inst0_out), .in1(I2), .out(xor_inst1_out));
assign O = xor_inst1_out;
endmodule

module corebit_const #(parameter value = 1) (output out);
  assign out = value;
endmodule

module corebit_and (input in0, input in1, output out);
  assign out = in0 & in1;
endmodule

module Or3xNone (input I0, input I1, input I2, output O);
wire orr_inst0_out;
coreir_orr #(.width(3)) orr_inst0(.in({I2,I1,I0}), .out(orr_inst0_out));
assign O = orr_inst0_out;
endmodule

module FullAdder (input CIN, output COUT, input I0, input I1, output O);
wire Or3xNone_inst0_O;
wire and_inst0_out;
wire and_inst1_out;
wire and_inst2_out;
wire fold_xor3None_inst0_O;
Or3xNone Or3xNone_inst0(.I0(and_inst0_out), .I1(and_inst1_out), .I2(and_inst2_out), .O(Or3xNone_inst0_O));
corebit_and and_inst0(.in0(I0), .in1(I1), .out(and_inst0_out));
corebit_and and_inst1(.in0(I1), .in1(CIN), .out(and_inst1_out));
corebit_and and_inst2(.in0(I0), .in1(CIN), .out(and_inst2_out));
fold_xor3None fold_xor3None_inst0(.I0(I0), .I1(I1), .I2(CIN), .O(fold_xor3None_inst0_O));
assign COUT = Or3xNone_inst0_O;
assign O = fold_xor3None_inst0_O;
endmodule

module Adder_unq1 (input CIN, output COUT, input [3:0] I0, input [3:0] I1, output [3:0] O);
wire FullAdder_inst0_COUT;
wire FullAdder_inst0_O;
wire FullAdder_inst1_COUT;
wire FullAdder_inst1_O;
wire FullAdder_inst2_COUT;
wire FullAdder_inst2_O;
wire FullAdder_inst3_COUT;
wire FullAdder_inst3_O;
FullAdder FullAdder_inst0(.CIN(CIN), .COUT(FullAdder_inst0_COUT), .I0(I0[0]), .I1(I1[0]), .O(FullAdder_inst0_O));
FullAdder FullAdder_inst1(.CIN(FullAdder_inst0_COUT), .COUT(FullAdder_inst1_COUT), .I0(I0[1]), .I1(I1[1]), .O(FullAdder_inst1_O));
FullAdder FullAdder_inst2(.CIN(FullAdder_inst1_COUT), .COUT(FullAdder_inst2_COUT), .I0(I0[2]), .I1(I1[2]), .O(FullAdder_inst2_O));
FullAdder FullAdder_inst3(.CIN(FullAdder_inst2_COUT), .COUT(FullAdder_inst3_COUT), .I0(I0[3]), .I1(I1[3]), .O(FullAdder_inst3_O));
assign COUT = FullAdder_inst3_COUT;
assign O = {FullAdder_inst3_O,FullAdder_inst2_O,FullAdder_inst1_O,FullAdder_inst0_O};
endmodule

module Adder (input CIN, output COUT, input [3:0] I0, input [3:0] I1, output [3:0] O);
wire bit_const_0_None_out;
wire [4:0] coreir_add5_inst0_out;
wire [4:0] coreir_add5_inst1_out;
corebit_const #(.value(0)) bit_const_0_None(.out(bit_const_0_None_out));
coreir_add #(.width(5)) coreir_add5_inst0(.in0({bit_const_0_None_out,I0[3],I0[2],I0[1],I0[0]}), .in1({bit_const_0_None_out,I1[3],I1[2],I1[1],I1[0]}), .out(coreir_add5_inst0_out));
coreir_add #(.width(5)) coreir_add5_inst1(.in0(coreir_add5_inst0_out), .in1({bit_const_0_None_out,bit_const_0_None_out,bit_const_0_None_out,bit_const_0_None_out,CIN}), .out(coreir_add5_inst1_out));
assign COUT = coreir_add5_inst1_out[4];
assign O = {coreir_add5_inst1_out[3],coreir_add5_inst1_out[2],coreir_add5_inst1_out[1],coreir_add5_inst1_out[0]};
endmodule

module DUT (input CIN, output COUT, input [3:0] I0, input [3:0] I1, output [3:0] O);
wire adder0_COUT;
wire [3:0] adder0_O;
wire adder1_COUT;
wire [3:0] adder1_O;
Adder adder0(.CIN(CIN), .COUT(adder0_COUT), .I0(I0), .I1(I1), .O(adder0_O));
Adder_unq1 adder1(.CIN(adder0_COUT), .COUT(adder1_COUT), .I0(adder0_O), .I1(adder0_O), .O(adder1_O));
assign COUT = adder1_COUT;
assign O = adder1_O;
endmodule

"""
