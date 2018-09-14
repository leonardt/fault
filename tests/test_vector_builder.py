import random
from bit_vector import BitVector
import fault
import common
from fault.actions import Poke, Expect, Eval, Step, Print
from fault.array import Array
from fault.vector_builder import VectorBuilder


def test_tester_basic():
    circ = common.TestBasicCircuit
    builder = VectorBuilder(circ)
    builder.process(Poke(circ.I, BitVector(0, 1)))
    builder.process(Expect(circ.O, BitVector(0, 1)))
    assert builder.vectors == [[BitVector(0, 1), BitVector(0, 1)]]
    builder.process(Eval())
    assert builder.vectors == [[BitVector(0, 1), BitVector(0, 1)],
                               [BitVector(0, 1), fault.AnyValue]]


def test_tester_clock():
    circ = common.TestBasicClkCircuit
    builder = VectorBuilder(circ)
    builder.process(Poke(circ.I, BitVector(0, 1)))
    builder.process(Print(circ.O))
    builder.process(Expect(circ.O, BitVector(0, 1)))
    assert builder.vectors == [
        [BitVector(0, 1), BitVector(0, 1), fault.AnyValue]
    ]
    builder.process(Poke(circ.CLK, BitVector(0, 1)))
    assert builder.vectors == [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)]
    ]
    builder.process(Step(circ.CLK, 1))
    assert builder.vectors == [
        [BitVector(0, 1), BitVector(0, 1), BitVector(0, 1)],
        [BitVector(0, 1), fault.AnyValue, BitVector(1, 1)]
    ]


def test_tester_nested_arrays():
    circ = common.TestNestedArraysCircuit
    builder = VectorBuilder(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        builder.process(Poke(circ.I[i], BitVector(val, 4)))
        builder.process(Expect(circ.O[i], BitVector(val, 4)))
        expected.append(val)
    assert builder.vectors == [[Array(expected, 3), Array(expected, 3)]]
