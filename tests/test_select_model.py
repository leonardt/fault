"""
Tests support for selecting different implementations of a DUT (or
subcomponents of a DUT)
"""
import magma as m
import fault
import hwtypes as ht
import os
import tempfile


class FullAdder(m.Circuit):
    io = m.IO(I0=m.In(m.Bit), I1=m.In(m.Bit), CIN=m.In(m.Bit),
              O=m.Out(m.Bit), COUT=m.Out(m.Bit))

    # Generate the sum
    m.wire(io.I0 ^ io.I1 ^ io.CIN, io.O)
    # Generate the carry
    m.wire(
        (io.I0 & io.I1) | (io.I1 & io.CIN) | (io.I0 & io.CIN),
        io.COUT
    )


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
        T = m.UInt[N]

        class Adder(m.Circuit):
            io = m.IO(I0=m.In(T), I1=m.In(T), CIN=m.In(m.Bit),
                      O=m.Out(T), COUT=m.Out(m.Bit))
            adders = [FullAdder() for _ in range(N)]
            adders = m.fold(adders, foldargs={"CIN": "COUT"})
            COUT, O = adders(I0=io.I0, I1=io.I1, CIN=io.CIN)
            m.wire(O, io.O)
            m.wire(COUT, io.COUT)
        return Adder

    def DefineAdderBehavioral(N):
        """
        Generate a behavioral adder
        """
        T = m.UInt[N]

        class Adder(m.Circuit):
            io = m.IO(I0=m.In(T), I1=m.In(T), CIN=m.In(m.Bit),
                      O=m.Out(T), COUT=m.Out(m.Bit))
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
        tester.compile_and_run(target="verilator", directory=directory,
                               magma_output="mlir-verilog")
        # Assert that the generated verilog generates two different adders
        with open(os.path.join(directory, "DUT.v"), "r") as f:
            assert f.read() == """\
module Adder(
  input  [3:0] I0,
               I1,
  input        CIN,
  output [3:0] O,
  output       COUT
);

  wire [4:0] _GEN = {1'h0, I0} + {1'h0, I1} + {4'h0, CIN};
  assign O = _GEN[3:0];
  assign COUT = _GEN[4];
endmodule

module FullAdder(
  input  I0,
         I1,
         CIN,
  output O,
         COUT
);

  assign O = I0 ^ I1 ^ CIN;
  assign COUT = I0 & I1 | I1 & CIN | I0 & CIN;
endmodule

module Adder_unq1(
  input  [3:0] I0,
               I1,
  input        CIN,
  output [3:0] O,
  output       COUT
);

  wire _FullAdder_inst3_O;
  wire _FullAdder_inst2_O;
  wire _FullAdder_inst2_COUT;
  wire _FullAdder_inst1_O;
  wire _FullAdder_inst1_COUT;
  wire _FullAdder_inst0_O;
  wire _FullAdder_inst0_COUT;
  FullAdder FullAdder_inst0 (
    .I0   (I0[0]),
    .I1   (I1[0]),
    .CIN  (CIN),
    .O    (_FullAdder_inst0_O),
    .COUT (_FullAdder_inst0_COUT)
  );
  FullAdder FullAdder_inst1 (
    .I0   (I0[1]),
    .I1   (I1[1]),
    .CIN  (_FullAdder_inst0_COUT),
    .O    (_FullAdder_inst1_O),
    .COUT (_FullAdder_inst1_COUT)
  );
  FullAdder FullAdder_inst2 (
    .I0   (I0[2]),
    .I1   (I1[2]),
    .CIN  (_FullAdder_inst1_COUT),
    .O    (_FullAdder_inst2_O),
    .COUT (_FullAdder_inst2_COUT)
  );
  FullAdder FullAdder_inst3 (
    .I0   (I0[3]),
    .I1   (I1[3]),
    .CIN  (_FullAdder_inst2_COUT),
    .O    (_FullAdder_inst3_O),
    .COUT (COUT)
  );
  assign O =
    {_FullAdder_inst3_O, _FullAdder_inst2_O, _FullAdder_inst1_O, _FullAdder_inst0_O};
endmodule

module DUT(
  input  [3:0] I0,
               I1,
  input        CIN,
  output [3:0] O,
  output       COUT
);

  wire [3:0] _adder0_O;
  wire       _adder0_COUT;
  Adder adder0 (
    .I0   (I0),
    .I1   (I1),
    .CIN  (CIN),
    .O    (_adder0_O),
    .COUT (_adder0_COUT)
  );
  Adder_unq1 adder1 (
    .I0   (_adder0_O),
    .I1   (_adder0_O),
    .CIN  (_adder0_COUT),
    .O    (O),
    .COUT (COUT)
  );
endmodule

"""  # noqa
