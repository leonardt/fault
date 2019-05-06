from fault.actions import Poke, Expect, Eval, Step, Print, Peek, Loop
from fault import Tester
from fault.actions import Poke, Expect, Eval, Step, Print, Peek, FileOpen, \
    FileRead, FileWrite, FileClose, Loop
from fault.file import File
import common


def test_action_strs():
    circ = common.TestBasicClkCircuit
    assert str(Poke(circ.I, 1)) == 'Poke(BasicClkCircuit.I, 1)'
    assert str(Expect(circ.O, 1)) == 'Expect(BasicClkCircuit.O, 1)'
    assert str(Eval()) == 'Eval()'
    assert str(Step(circ.CLK, 1)) == 'Step(BasicClkCircuit.CLK, steps=1)'
    assert str(Print(circ.O, "%08x")) == 'Print(BasicClkCircuit.O, "%08x")'
    assert str(Peek(circ.O)) == 'Peek(BasicClkCircuit.O)'
    index = f"__fault_loop_var_action_0"
    assert str(Loop(12, index, [Peek(circ.O), Poke(circ.I, 1)])) == \
        f'Loop(12, {index}, ' \
        f'[Peek(BasicClkCircuit.O), Poke(BasicClkCircuit.I, 1)])'
    file = File("my_file", Tester(circ))
    assert str(FileOpen(file)) == 'FileOpen(File<"my_file">)'
    assert str(FileRead(file, 1)) == 'FileRead(File<"my_file">, 1)'
    assert str(FileWrite(file, 3, 1)) == 'FileWrite(File<"my_file">, 3, 1)'
    assert str(FileClose(file)) == 'FileClose(File<"my_file">)'
