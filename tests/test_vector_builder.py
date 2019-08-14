import random
from hwtypes import BitVector
import fault
from fault.actions import Poke, Expect, Eval, Step, Print
from fault.array import Array
from fault.vector_builder import VectorBuilder
from .common import (TestBasicCircuit, TestBasicClkCircuit,
                     TestNestedArraysCircuit)


def test_tester_basic():
    circ = TestBasicCircuit
    builder = VectorBuilder(circ)
    builder.process(Poke(circ.I, BitVector[1](0)))
    builder.process(Expect(circ.O, BitVector[1](0)))
    assert builder.vectors == [[BitVector[1](0), BitVector[1](0)]]
    builder.process(Eval())
    assert builder.vectors == [[BitVector[1](0), BitVector[1](0)],
                               [BitVector[1](0), fault.AnyValue]]


def test_tester_clock():
    circ = TestBasicClkCircuit
    builder = VectorBuilder(circ)
    builder.process(Poke(circ.I, BitVector[1](0)))
    builder.process(Print("%x", circ.O))
    builder.process(Expect(circ.O, BitVector[1](0)))
    assert builder.vectors == [
        [BitVector[1](0), BitVector[1](0), fault.AnyValue]
    ]
    builder.process(Poke(circ.CLK, BitVector[1](0)))
    assert builder.vectors == [
        [BitVector[1](0), BitVector[1](0), BitVector[1](0)]
    ]
    builder.process(Step(circ.CLK, 1))
    assert builder.vectors == [
        [BitVector[1](0), BitVector[1](0), BitVector[1](0)],
        [BitVector[1](0), fault.AnyValue, BitVector[1](1)]
    ]


def test_tester_nested_arrays():
    circ = TestNestedArraysCircuit
    builder = VectorBuilder(circ)
    expected = []
    for i in range(3):
        val = random.randint(0, (1 << 4) - 1)
        builder.process(Poke(circ.I[i], BitVector[4](val)))
        builder.process(Expect(circ.O[i], BitVector[4](val)))
        expected.append(val)
    assert builder.vectors == [[Array(expected, 3), Array(expected, 3)]]
