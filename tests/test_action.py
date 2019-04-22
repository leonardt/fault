from fault.actions import Poke, Expect, Eval, Step, Print, Peek, Loop
import common


def test_action_strs():
    circ = common.TestBasicClkCircuit
    assert str(Poke(circ.I, 1)) == 'Poke(BasicClkCircuit.I, 1)'
    assert str(Expect(circ.O, 1)) == 'Expect(BasicClkCircuit.O, 1)'
    assert str(Eval()) == 'Eval()'
    assert str(Step(circ.CLK, 1)) == 'Step(BasicClkCircuit.CLK, steps=1)'
    assert str(Print(circ.O, "%08x")) == 'Print(BasicClkCircuit.O, "%08x")'
    assert str(Peek(circ.O)) == 'Peek(BasicClkCircuit.O)'
    assert str(Loop(12, [Peek(circ.O), Poke(circ.I, 1)])) == \
        'Loop(12, [Peek(BasicClkCircuit.O), Poke(BasicClkCircuit.I, 1)])'
