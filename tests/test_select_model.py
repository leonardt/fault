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

        # Compile a structural version in a sub-directory "structural"
        structural_dir = os.path.join(tempdir, "structural")
        os.mkdir(structural_dir)
        m.compile(os.path.join(structural_dir, "Adder"),
                  DefineAdderStructural(4), output="coreir-verilog")

        # Note, some wonkiness in the magma/coreir backend makes compiling
        # twice behave weirdly, will investigate, for now we work around this
        # by resetting the state of the magma compiler
        m.backend.coreir_.CoreIRContextSingleton().reset_instance()
        m.clear_cachedFunctions()

        # Compile a behavioral version
        behavioral_dir = os.path.join(tempdir, "behavioral")
        os.mkdir(behavioral_dir)
        m.compile(os.path.join(behavioral_dir, "Adder"),
                  DefineAdderBehavioral(4), output="coreir-verilog")

        # Reset magma compiler state again
        m.backend.coreir_.CoreIRContextSingleton().reset_instance()
        m.clear_cachedFunctions()

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
                adder = DeclareAdder(4)()
                O, COUT = adder(io)
                io.O <= O
                io.COUT <= COUT

        # Generic adder test bench using DUT
        tester = fault.Tester(DUT)
        for i in range(10):
            tester.circuit.I0 = I0 = ht.BitVector.random(4)
            tester.circuit.I1 = I1 = ht.BitVector.random(4)
            tester.circuit.CIN = CIN = ht.BitVector.random(1)[0]
            tester.eval()
            tester.circuit.O.expect(I0 + I1 + CIN)
            tester.circuit.COUT.expect(
                (I0.zext(1) + I1.zext(1) + ht.BitVector[5](CIN))[-1])

        # Run the test bench with the structural version by including the
        # structural_directory
        tester.compile_and_run(target="verilator",
                               include_directories=[structural_dir])

        # Run again with the behavioral version
        tester.compile_and_run(target="verilator",
                               include_directories=[behavioral_dir])
