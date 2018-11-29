# Inspecting

The tester defines a `__str__` method that includes an enumeration of the action sequence. It can be useful for mapping errors in the test bench back to the associated action.

For example, this code
```python
   tester = fault.Tester(circ, circ.CLK, default_print_format_str="%08x")
   tester.poke(circ.I, 0)
   tester.eval()
   tester.expect(circ.O, 0)
   tester.poke(circ.CLK, 0)
   tester.step()
   tester.print(circ.O)
   print(tester)
```

will print out

```
<fault.tester.Tester object at 0x112208358>
Actions:
   0: Poke(BasicClkCircuit.I, 0)
   1: Eval()
   2: Expect(BasicClkCircuit.O, 0)
   3: Poke(BasicClkCircuit.CLK, 0)
   4: Step(BasicClkCircuit.CLK, steps=1)
   5: Print(BasicClkCircuit.O, "%08x")

Actions:
    0: Poke(BasicClkCircuit.I, 0)
    1: Eval()
    2: Expect(BasicClkCircuit.O, 0)
    3: Poke(BasicClkCircuit.CLK, 0)
    4: Step(BasicClkCircuit.CLK, steps=1)
    5: Print(BasicClkCircuit.O, "%08x")
```
