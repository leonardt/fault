from fault.actions import Poke, Expect, Eval, Step, Print, Peek, Loop
import common


def test_action_strs():
    circ = common.TestBasicClkCircuit
    assert str(Poke(circ.I, 1)) == 'Poke(BasicClkCircuit.I, 1)'
    assert str(Expect(circ.O, 1)) == 'Expect(BasicClkCircuit.O, 1)'
    assert str(Eval()) == 'Eval()'
    assert str(Step(circ.CLK, 1)) == 'Step(BasicClkCircuit.CLK, steps=1)'
    assert str(Print("%08x", circ.O)) == 'Print("%08x", BasicClkCircuit.O)'
    assert str(Peek(circ.O)) == 'Peek(BasicClkCircuit.O)'
    index = f"__fault_loop_var_action_0"
    assert str(Loop(12, index, [Peek(circ.O), Poke(circ.I, 1)])) == \
        f'Loop(12, {index}, ' \
        f'[Peek(BasicClkCircuit.O), Poke(BasicClkCircuit.I, 1)])'
