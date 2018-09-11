from fault.actions import Poke, Expect, Eval, Step
import common


def test_action_strs():
    circ = common.TestBasicClkCircuit
    assert str(Poke(circ.I, 1)) == 'Poke(BasicClkCircuit.I, 1)'
    assert str(Expect(circ.O, 1)) == 'Expect(BasicClkCircuit.O, 1)'
    assert str(Eval()) == 'Eval()'
    assert str(Step(circ.CLK, 1)) == 'Step(BasicClkCircuit.CLK, steps=1)'
