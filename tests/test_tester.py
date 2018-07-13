import magma as m
import fault
from bit_vector import BitVector


def test_tester_basic():
    circ = m.DefineCircuit("test_circuit", "I", m.In(m.Bit), "O",
                           m.Out(m.Bit))
    m.wire(circ.I, circ.O)
    m.EndDefine()
    tester = fault.Tester(circ)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    assert tester.test_vectors == [[BitVector(0, 1), BitVector(0, 1)]]
    tester.eval()
    assert tester.test_vectors == [[BitVector(0, 1), BitVector(0, 1)],
                                   [BitVector(0, 1), BitVector(0, 1)]]


def test_tester_clock():
    circ = m.DefineCircuit("test_circuit_clock", "I", m.In(m.Bit), "O",
                           m.Out(m.Bit), "CLK", m.In(m.Clock))
    m.wire(circ.I, circ.O)
    m.EndDefine()
    tester = fault.Tester(circ, circ.CLK)
    tester.poke(circ.I, 0)
    tester.expect(circ.O, 0)
    assert tester.test_vectors == [
        [BitVector(0, 1), BitVector(0, 1), BitVector(None, 1)]
    ]
    tester.poke(circ.CLK, 0)
    assert tester.test_vectors == [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)]
    ]
    tester.step()
    assert tester.test_vectors == [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)],
        [BitVector(0, 1), BitVector(0, 1), BitVector(1, 1)]
    ]
