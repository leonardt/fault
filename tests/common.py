import magma as m
import mantle


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
TestArrayCircuit = define_simple_circuit(m.Array[3, m.Bit], "ArrayCircuit")
TestByteCircuit = define_simple_circuit(m.Bits[8], "ByteCircuit")
TestUInt32Circuit = define_simple_circuit(m.UInt[32], "UInt32Circuit")
TestSIntCircuit = define_simple_circuit(m.SInt[4], "SIntCircuit")
TestNestedArraysCircuit = define_simple_circuit(m.Array[3, m.Bits[4]],
                                                "NestedArraysCircuit")
TestDoubleNestedArraysCircuit = define_simple_circuit(
    m.Array[2, m.Array[3, m.Bits[4]]], "DoubleNestedArraysCircuit")
TestBasicClkCircuit = define_simple_circuit(m.Bit, "BasicClkCircuit", True)
TestBasicClkCircuitCopy = define_simple_circuit(m.Bit, "BasicClkCircuitCopy",
                                                True)
TestTupleCircuit = define_simple_circuit(m.Tuple(a=m.Bits[4], b=m.Bits[4]),
                                         "TupleCircuit")

T = m.Bits[3]


class TestPeekCircuit(m.Circuit):
    __test__ = False   # Disable pytest discovery
    IO = ["I", m.In(T), "O0", m.Out(T), "O1", m.Out(T)]

    @classmethod
    def definition(io):
        m.wire(io.I, io.O0)
        m.wire(io.I, io.O1)


class ConfigReg(m.Circuit):
    IO = ["D", m.In(m.Bits[2]), "Q", m.Out(m.Bits[2])] + \
        m.ClockInterface(has_ce=True)

    @classmethod
    def definition(io):
        reg = mantle.Register(2, has_ce=True, name="conf_reg")
        io.Q <= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    IO = ["a", m.In(m.UInt[16]),
          "b", m.In(m.UInt[16]),
          "c", m.Out(m.UInt[16]),
          "config_data", m.In(m.Bits[2]),
          "config_en", m.In(m.Enable),
          ] + m.ClockInterface()

    @classmethod
    def definition(io):
        opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
        io.c <= mantle.mux(
            # udiv not implemented
            # [io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b], opcode)
            # use arbitrary fourth op
            [io.a + io.b, io.a - io.b, io.a * io.b, io.b - io.a], opcode)


class AndCircuit(m.Circuit):
    IO = ["I0", m.In(m.Bit), "I1", m.In(m.Bit), "O", m.Out(m.Bit)]

    @classmethod
    def definition(io):
        io.O <= io.I0 & io.I1
