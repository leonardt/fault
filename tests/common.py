import magma as m
import pytest


def define_simple_circuit(T, circ_name, has_clk=False):
    class _Circuit(m.Circuit):
        __test__ = False   # Disable pytest discovery
        name = circ_name
        IO = ["I", m.In(T), "O", m.Out(T)]
        if has_clk:
            IO += ["CLK", m.In(m.Clock)]

        @classmethod
        def definition(io):
            m.wire(io.I, io.O)

    return _Circuit


TestBasicCircuit = define_simple_circuit(m.Bit, "BasicCircuit")
TestNestedArraysCircuit = define_simple_circuit(m.Array(3, m.Bits(4)),
                                                "NestedArraysCircuit")
TestBasicClkCircuit = define_simple_circuit(m.Bit, "BasicClkCircuit", True)
