from fault import PythonTester
from ..common import AndCircuit


def test_interactive_basic():
    tester = PythonTester(AndCircuit)
    tester.poke(AndCircuit.I0, 0)
    tester.poke(AndCircuit.I1, 1)
    tester.eval()
    tester.expect(AndCircuit.O, 0)
