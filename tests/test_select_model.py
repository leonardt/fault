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

    with tempfile.TemporaryDirectory() as tempdir:

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
module coreir_orr #(parameter width=1) (
  input [width-1:0] in,
  output out
);
  assign out = |in;

endmodule  // coreir_orr

module coreir_add #(parameter width=1) (
  input [width-1:0] in0,
  input [width-1:0] in1,
  output [width-1:0] out
);
  assign out = in0 + in1;

endmodule  // coreir_add

module corebit_xor (
  input in0,
  input in1,
  output out
);
  assign out = in0 ^ in1;

endmodule  // corebit_xor

module fold_xor3None (
  input  I0,
  input  I1,
  input  I2,
  output  O
);


  wire  xor_inst0__in0;
  wire  xor_inst0__in1;
  wire  xor_inst0__out;
  corebit_xor xor_inst0(
    .in0(xor_inst0__in0),
    .in1(xor_inst0__in1),
    .out(xor_inst0__out)
  );

  wire  xor_inst1__in0;
  wire  xor_inst1__in1;
  wire  xor_inst1__out;
  corebit_xor xor_inst1(
    .in0(xor_inst1__in0),
    .in1(xor_inst1__in1),
    .out(xor_inst1__out)
  );

  assign xor_inst0__in0 = I0;

  assign xor_inst0__in1 = I1;

  assign xor_inst1__in1 = I2;

  assign O = xor_inst1__out;

  assign xor_inst1__in0 = xor_inst0__out;


endmodule  // fold_xor3None

module corebit_const #(parameter value=1) (
  output out
);
  assign out = value;

endmodule  // corebit_const

module corebit_and (
  input in0,
  input in1,
  output out
);
  assign out = in0 & in1;

endmodule  // corebit_and

module Or3xNone (
  input  I0,
  input  I1,
  input  I2,
  output  O
);


  // Instancing generated Module: coreir.orr(width:3)
  wire [2:0] orr_inst0__in;
  wire  orr_inst0__out;
  coreir_orr #(.width(3)) orr_inst0(
    .in(orr_inst0__in),
    .out(orr_inst0__out)
  );

  assign orr_inst0__in[0] = I0;

  assign orr_inst0__in[1] = I1;

  assign orr_inst0__in[2] = I2;

  assign O = orr_inst0__out;


endmodule  // Or3xNone

module FullAdder (
  input  CIN,
  output  COUT,
  input  I0,
  input  I1,
  output  O
);


  wire  Or3xNone_inst0__I0;
  wire  Or3xNone_inst0__I1;
  wire  Or3xNone_inst0__I2;
  wire  Or3xNone_inst0__O;
  Or3xNone Or3xNone_inst0(
    .I0(Or3xNone_inst0__I0),
    .I1(Or3xNone_inst0__I1),
    .I2(Or3xNone_inst0__I2),
    .O(Or3xNone_inst0__O)
  );

  wire  and_inst0__in0;
  wire  and_inst0__in1;
  wire  and_inst0__out;
  corebit_and and_inst0(
    .in0(and_inst0__in0),
    .in1(and_inst0__in1),
    .out(and_inst0__out)
  );

  wire  and_inst1__in0;
  wire  and_inst1__in1;
  wire  and_inst1__out;
  corebit_and and_inst1(
    .in0(and_inst1__in0),
    .in1(and_inst1__in1),
    .out(and_inst1__out)
  );

  wire  and_inst2__in0;
  wire  and_inst2__in1;
  wire  and_inst2__out;
  corebit_and and_inst2(
    .in0(and_inst2__in0),
    .in1(and_inst2__in1),
    .out(and_inst2__out)
  );

  wire  fold_xor3None_inst0__I0;
  wire  fold_xor3None_inst0__I1;
  wire  fold_xor3None_inst0__I2;
  wire  fold_xor3None_inst0__O;
  fold_xor3None fold_xor3None_inst0(
    .I0(fold_xor3None_inst0__I0),
    .I1(fold_xor3None_inst0__I1),
    .I2(fold_xor3None_inst0__I2),
    .O(fold_xor3None_inst0__O)
  );

  assign Or3xNone_inst0__I0 = and_inst0__out;

  assign Or3xNone_inst0__I1 = and_inst1__out;

  assign Or3xNone_inst0__I2 = and_inst2__out;

  assign COUT = Or3xNone_inst0__O;

  assign and_inst0__in0 = I0;

  assign and_inst0__in1 = I1;

  assign and_inst1__in0 = I1;

  assign and_inst1__in1 = CIN;

  assign and_inst2__in0 = I0;

  assign and_inst2__in1 = CIN;

  assign fold_xor3None_inst0__I0 = I0;

  assign fold_xor3None_inst0__I1 = I1;

  assign fold_xor3None_inst0__I2 = CIN;

  assign O = fold_xor3None_inst0__O;


endmodule  // FullAdder

module Adder_unq1 (
  input  CIN,
  output  COUT,
  input [3:0] I0,
  input [3:0] I1,
  output [3:0] O
);


  wire  FullAdder_inst0__CIN;
  wire  FullAdder_inst0__COUT;
  wire  FullAdder_inst0__I0;
  wire  FullAdder_inst0__I1;
  wire  FullAdder_inst0__O;
  FullAdder FullAdder_inst0(
    .CIN(FullAdder_inst0__CIN),
    .COUT(FullAdder_inst0__COUT),
    .I0(FullAdder_inst0__I0),
    .I1(FullAdder_inst0__I1),
    .O(FullAdder_inst0__O)
  );

  wire  FullAdder_inst1__CIN;
  wire  FullAdder_inst1__COUT;
  wire  FullAdder_inst1__I0;
  wire  FullAdder_inst1__I1;
  wire  FullAdder_inst1__O;
  FullAdder FullAdder_inst1(
    .CIN(FullAdder_inst1__CIN),
    .COUT(FullAdder_inst1__COUT),
    .I0(FullAdder_inst1__I0),
    .I1(FullAdder_inst1__I1),
    .O(FullAdder_inst1__O)
  );

  wire  FullAdder_inst2__CIN;
  wire  FullAdder_inst2__COUT;
  wire  FullAdder_inst2__I0;
  wire  FullAdder_inst2__I1;
  wire  FullAdder_inst2__O;
  FullAdder FullAdder_inst2(
    .CIN(FullAdder_inst2__CIN),
    .COUT(FullAdder_inst2__COUT),
    .I0(FullAdder_inst2__I0),
    .I1(FullAdder_inst2__I1),
    .O(FullAdder_inst2__O)
  );

  wire  FullAdder_inst3__CIN;
  wire  FullAdder_inst3__COUT;
  wire  FullAdder_inst3__I0;
  wire  FullAdder_inst3__I1;
  wire  FullAdder_inst3__O;
  FullAdder FullAdder_inst3(
    .CIN(FullAdder_inst3__CIN),
    .COUT(FullAdder_inst3__COUT),
    .I0(FullAdder_inst3__I0),
    .I1(FullAdder_inst3__I1),
    .O(FullAdder_inst3__O)
  );

  assign FullAdder_inst0__CIN = CIN;

  assign FullAdder_inst1__CIN = FullAdder_inst0__COUT;

  assign FullAdder_inst0__I0 = I0[0];

  assign FullAdder_inst0__I1 = I1[0];

  assign O[0] = FullAdder_inst0__O;

  assign FullAdder_inst2__CIN = FullAdder_inst1__COUT;

  assign FullAdder_inst1__I0 = I0[1];

  assign FullAdder_inst1__I1 = I1[1];

  assign O[1] = FullAdder_inst1__O;

  assign FullAdder_inst3__CIN = FullAdder_inst2__COUT;

  assign FullAdder_inst2__I0 = I0[2];

  assign FullAdder_inst2__I1 = I1[2];

  assign O[2] = FullAdder_inst2__O;

  assign COUT = FullAdder_inst3__COUT;

  assign FullAdder_inst3__I0 = I0[3];

  assign FullAdder_inst3__I1 = I1[3];

  assign O[3] = FullAdder_inst3__O;


endmodule  // Adder_unq1

module Adder (
  input  CIN,
  output  COUT,
  input [3:0] I0,
  input [3:0] I1,
  output [3:0] O
);


  wire  bit_const_0_None__out;
  corebit_const #(.value(0)) bit_const_0_None(
    .out(bit_const_0_None__out)
  );

  // Instancing generated Module: coreir.add(width:5)
  wire [4:0] coreir_add5_inst0__in0;
  wire [4:0] coreir_add5_inst0__in1;
  wire [4:0] coreir_add5_inst0__out;
  coreir_add #(.width(5)) coreir_add5_inst0(
    .in0(coreir_add5_inst0__in0),
    .in1(coreir_add5_inst0__in1),
    .out(coreir_add5_inst0__out)
  );

  // Instancing generated Module: coreir.add(width:5)
  wire [4:0] coreir_add5_inst1__in0;
  wire [4:0] coreir_add5_inst1__in1;
  wire [4:0] coreir_add5_inst1__out;
  coreir_add #(.width(5)) coreir_add5_inst1(
    .in0(coreir_add5_inst1__in0),
    .in1(coreir_add5_inst1__in1),
    .out(coreir_add5_inst1__out)
  );

  assign coreir_add5_inst0__in0[4] = bit_const_0_None__out;

  assign coreir_add5_inst0__in1[4] = bit_const_0_None__out;

  assign coreir_add5_inst1__in1[1] = bit_const_0_None__out;

  assign coreir_add5_inst1__in1[2] = bit_const_0_None__out;

  assign coreir_add5_inst1__in1[3] = bit_const_0_None__out;

  assign coreir_add5_inst1__in1[4] = bit_const_0_None__out;

  assign coreir_add5_inst0__in0[0] = I0[0];

  assign coreir_add5_inst0__in0[1] = I0[1];

  assign coreir_add5_inst0__in0[2] = I0[2];

  assign coreir_add5_inst0__in0[3] = I0[3];

  assign coreir_add5_inst0__in1[0] = I1[0];

  assign coreir_add5_inst0__in1[1] = I1[1];

  assign coreir_add5_inst0__in1[2] = I1[2];

  assign coreir_add5_inst0__in1[3] = I1[3];

  assign coreir_add5_inst1__in0[4:0] = coreir_add5_inst0__out[4:0];

  assign coreir_add5_inst1__in1[0] = CIN;

  assign O[0] = coreir_add5_inst1__out[0];

  assign O[1] = coreir_add5_inst1__out[1];

  assign O[2] = coreir_add5_inst1__out[2];

  assign O[3] = coreir_add5_inst1__out[3];

  assign COUT = coreir_add5_inst1__out[4];


endmodule  // Adder

module DUT (
  input  CIN,
  output  COUT,
  input [3:0] I0,
  input [3:0] I1,
  output [3:0] O
);


  wire  adder0__CIN;
  wire  adder0__COUT;
  wire [3:0] adder0__I0;
  wire [3:0] adder0__I1;
  wire [3:0] adder0__O;
  Adder adder0(
    .CIN(adder0__CIN),
    .COUT(adder0__COUT),
    .I0(adder0__I0),
    .I1(adder0__I1),
    .O(adder0__O)
  );

  wire  adder1__CIN;
  wire  adder1__COUT;
  wire [3:0] adder1__I0;
  wire [3:0] adder1__I1;
  wire [3:0] adder1__O;
  Adder_unq1 adder1(
    .CIN(adder1__CIN),
    .COUT(adder1__COUT),
    .I0(adder1__I0),
    .I1(adder1__I1),
    .O(adder1__O)
  );

  assign adder0__CIN = CIN;

  assign adder1__CIN = adder0__COUT;

  assign adder0__I0[3:0] = I0[3:0];

  assign adder0__I1[3:0] = I1[3:0];

  assign adder1__I0[3:0] = adder0__O[3:0];

  assign adder1__I1[3:0] = adder0__O[3:0];

  assign COUT = adder1__COUT;

  assign O[3:0] = adder1__O[3:0];


endmodule  // DUT

"""
