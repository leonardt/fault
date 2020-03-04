from fault import Tester
from fault.actions import Poke, Expect, Eval, Step, Print, Peek, FileOpen, \
    FileRead, FileWrite, FileClose, Loop
from fault.file import File
from .common import TestBasicClkCircuit


def test_action_strs():
    circ = TestBasicClkCircuit
    assert str(Poke(circ.I, 1)) == 'Poke(BasicClkCircuit.I, 1)'
    assert str(Expect(circ.O, 1)) == 'Expect(BasicClkCircuit.O, 1)'
    assert str(Eval()) == 'Eval()'
    assert str(Step(circ.CLK, 1)) == 'Step(BasicClkCircuit.CLK, steps=1)'
    assert str(Print("%08x", circ.O)) == 'Print("%08x", BasicClkCircuit.O)'
    assert str(Peek(circ.O)) == 'Peek(BasicClkCircuit.O)'
    index = f"__fault_loop_var_action_0"
    loop_body = [Peek(circ.O), Poke(circ.I, 1)]
    assert str(Loop(12, index, loop_body)) == \
        f'Loop(12, {index}, ' \
        f'[Peek(BasicClkCircuit.O), Poke(BasicClkCircuit.I, 1)], up)'
    file = File("my_file", Tester(circ), "r", 1, "little")
    assert str(FileOpen(file)) == 'FileOpen(File<"my_file">)'
    assert str(FileRead(file)) == 'FileRead(File<"my_file">)'
    assert str(FileWrite(file, 3)) == 'FileWrite(File<"my_file">, 3)'
    assert str(FileClose(file)) == 'FileClose(File<"my_file">)'
