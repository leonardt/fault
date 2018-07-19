import magma as m


class TestNestedArraysCircuit(m.Circuit):
    IO = ["I", m.In(m.Array(3, m.Bits(4))), "O", m.Out(m.Array(3, m.Bits(4)))]

    @classmethod
    def definition(io):
        m.wire(io.I, io.O)
