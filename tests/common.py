import magma as m


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
TestArrayCircuit = define_simple_circuit(m.Array(3, m.Bit), "ArrayCircuit")
TestSIntCircuit = define_simple_circuit(m.SInt(3), "SIntCircuit")
TestNestedArraysCircuit = define_simple_circuit(m.Array(3, m.Bits(4)),
                                                "NestedArraysCircuit")
TestDoubleNestedArraysCircuit = define_simple_circuit(
    m.Array(2, m.Array(3, m.Bits(4))), "DoubleNestedArraysCircuit")
TestBasicClkCircuit = define_simple_circuit(m.Bit, "BasicClkCircuit", True)
TestBasicClkCircuitCopy = define_simple_circuit(m.Bit, "BasicClkCircuitCopy",
                                                True)
TestTupleCircuit = define_simple_circuit(m.Tuple(a=m.Bit, b=m.Bit),
                                         "TupleCircuit")

T = m.Bits(3)


class TestPeekCircuit(m.Circuit):
    __test__ = False   # Disable pytest discovery
    IO = ["I", m.In(T), "O0", m.Out(T), "O1", m.Out(T)]

    @classmethod
    def definition(io):
        m.wire(io.I, io.O0)
        m.wire(io.I, io.O1)
