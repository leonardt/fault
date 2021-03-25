from fault import PythonTester
from ..common import AndCircuit, SimpleALU, TestTupleCircuit, \
    TestNestedArraysCircuit, TestNestedArrayTupleCircuit
from hwtypes import BitVector
from mantle import DefineCounter


def test_interactive_basic(capsys):
    tester = PythonTester(AndCircuit)
    tester.poke(AndCircuit.I0, 0)
    tester.poke(AndCircuit.I1, 1)
    tester.eval()
    tester.expect(AndCircuit.O, 0)
    tester.poke(AndCircuit.I0, 1)
    tester.eval()
    tester.assert_(tester.peek(AndCircuit.O) == 1)
    tester.print("Hello %d\n", AndCircuit.O)
    assert capsys.readouterr()[0] == "Hello 1\n"


def test_interactive_setattr():
    tester = PythonTester(AndCircuit)
    tester.circuit.I0 = 1
    tester.circuit.I1 = 1
    tester.eval()
    tester.circuit.O.expect(1)


def test_interactive_clock():
    tester = PythonTester(SimpleALU, SimpleALU.CLK)
    tester.circuit.a = 0xDEAD
    tester.circuit.b = 0xBEEF
    tester.circuit.CLK = 0
    tester.circuit.config_data = 1
    tester.circuit.config_en = 1
    tester.advance_cycle()
    tester.circuit.c.expect(BitVector[16](0xDEAD) - BitVector[16](0xBEEF))


def test_counter():
    Counter4 = DefineCounter(4)
    tester = PythonTester(Counter4, Counter4.CLK)
    tester.CLK = 0
    tester.wait_until_high(Counter4.O[3])
    tester.circuit.O.expect(1 << 3)
    tester.wait_until_low(Counter4.O[3])
    tester.circuit.O.expect(0)


def test_tuple():
    tester = PythonTester(TestTupleCircuit)
    tester.circuit.I = (4, 2)
    tester.eval()
    tester.circuit.O.expect((4, 2))
    tester.circuit.I = {"a": 4, "b": 2}
    tester.eval()
    tester.circuit.O.expect({"a": 4, "b": 2})


def test_nested_arrays():
    tester = PythonTester(TestTupleCircuit)
    tester.circuit.I = (4, 2)
    tester.eval()
    tester.circuit.O.expect((4, 2))
    tester.circuit.I = {"a": 4, "b": 2}
    tester.eval()
    tester.circuit.O.expect({"a": 4, "b": 2})


def test_tester_nested_arrays_bulk():
    tester = PythonTester(TestNestedArraysCircuit)
    expected = []
    val = [BitVector.random(4) for _ in range(3)]
    tester.poke(TestNestedArraysCircuit.I, val)
    tester.eval()
    tester.expect(TestNestedArraysCircuit.O, val)


def test_tester_nested_array_tuple():
    tester = PythonTester(TestNestedArrayTupleCircuit)
    expected = []
    val = (BitVector.random(4), BitVector.random(4))
    tester.poke(TestNestedArrayTupleCircuit.I, val)
    tester.eval()
    tester.expect(TestNestedArrayTupleCircuit.O, val)
