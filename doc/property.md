**NOTE** Property support is experimental, please submit bug reports and
feature requests via GitHub Issues.

Fault provides two interfaces for defining temporal assertions.  The firt uses
a magic implementation of the `__or__` and `__ror__` methods to define custom
"infix" operators.  The second provides an interface to provide strings
containing SVA operator syntax.
# Infix Operator Interface
This interface overloads the use of the `|` operator to define a "custom infix"
operator.  Here's an example of a property where `io.I` being high implies that
the value (driver) of `io.O` will be high one cycle later.
```python
f.assert_(io.I | f.implies | f.delay[1] | (io.O.value() == 0),
          on=f.posedge(io.CLK))
```
## Operators
* `f.implies` corresponds to SVA `|->`
* `f.delay[N]` corresponds to SVA `##N`
* `f.delay[M:N]` corresponds to SVA `##[M:N]`
* `f.delay[0:]` corresponds to SVA `##[*]`
* `f.delay[1:]` corresponds to SVA `##[+]`
* `f.repeat[N]` corresponds to SVA `[*N]`
* `f.repeat[0:]` corresponds to SVA `[*]`
* `f.repeat[1:]` corresponds to SVA `[+]`
* `f.goto[N]` corresponds to SVA `[-> N]`
* `f.goto[M:N]` corresponds to SVA `[-> M:N]`
* `f.eventually` corresponds to SVA `s_eventually`
* `f.throughout` corresponds to SVA `throughout`
* `f.until` corresponds to SVA `until`
* `f.until_with` corresponds to SVA `until_with`
* `f.inside` corresponds to SV `inside`

# SVA 
Use the `f.sva` function to construct sva properties by interleaving magma
signal/expressions and SVA operators. Here's a simple example:
```python
f.assert_(f.sva(io.I, "|-> ##1", io.O.value() == 0),
          on=f.posedge(io.CLK))
```

# System and Sampled Value Functions
* `f.onehot0`
* `f.onehot`
* `f.countones`
* `f.isunknown`
* `f.past`
* `f.rose`
* `f.fell`
* `f.stable`

# Other
* `f.not_` negates property

# Compile Guards (ifdef)
Use the `compile_guard` parameter and pass a string for the variable to guard
the property.
```python
f.assert_(..., compile_guard="ASSERT_ON", ...)
```

This will wrap the generated property inside a macro.
```verilog
`ifdef ASSERT_ON
    ...
`endif
```

For multiple guards, you can pass a list of strings, for example:
```python
f.assert_(..., compile_guard=["ASSERT_ON", "FORMAL_ON"], ...)
```

will produce
```verilog
`ifdef ASSERT_ON
    `ifdef FORMAL_ON
        ...
    `endif
`endif
```

**NOTE**: One issue with using a compile guard is that when the macro is disabled
magma/fault will produce dangling wires (these are used inside the body
of the macro which has been disabled).  As a temporary measure, fault will generate
these wires with the prefix `_FAULT_ASSERT_WIRE_` so you can direct your lint
tool to ignore these dangling wires (e.g. when you disable macros for synthesis).
The prefix can be chagned by setting the parameter `inline_wire_prefix` when
invoking `f.assert_`.

# Disable If
Use the `disable_iff` parameter and pass a signal or expression, for example
with a negedge RESET:
```python
f.assert_(..., on=f.posedge(io.CLK), disable_iff=f.not_(io.RESETN), ...)
```

# Name
Use the `name` parameter to give a property a name in the generated code.

For example,
```python
f.assert_(..., name="my_property")
```
will insert `my_property:` before the generated property code.

# Helper function for default clock/reset
A useful pattern is leveraging magma's automatic clock wiring logic to handle
default clock and reset values so the user doesn't have to provide them for
most assertions where the default clock is obvious and will be wired up
automatically.

To do this, create a temporary value of the approriate type and use that for
the on/disable_iff parameter.  This undriven temporary value will be
automatically wired up by magma.   We leave this to the user rather than having
it built-in so the user can control the Clock type or the reset type/semantics.

Here's an example:
```python
def my_assert(property, on=None, disable_iff=None):
    # If needed, create undriven clock/reset temporaries, will be driven by
    # automatic clock wiring logic
    if on is None:
        on = f.posedge(m.Clock())
    if disable_iff is None:
        disable_iff = f.not_(m.ResetN())
    f.assert_(property, on=on, disable_iff=disable_iff)

class Main(m.Circuit):
    io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8]))
    io += m.ClockIO(has_resetn=True)
    io.O @= m.Register(T=m.Bits[8], reset_type=m.ResetN)()(io.I)
    my_assert(io.I | f.implies | f.delay[1] | io.O)
```

# Examples
Here are some representative examples, for a complete set of examples and
corresponding test cases, see
[tests/test_property.py](../tests/test_property.py).

## Basic assertion
Here's an example of a basic implication/delay assertion on a register.
```python
class Main(m.Circuit):
    io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8])) + m.ClockIO()
    io.O @= m.Register(T=m.Bits[8])()(io.I)
    # SVA
    f.assert_(f.sva(io.I, "|-> ##1", io.O.value() == 0),
              on=f.posedge(io.CLK))
    # Infix
    f.assert_(io.I | f.implies | f.delay[1] | (io.O.value() == 0),
              on=f.posedge(io.CLK))
```

## Variable Delay
Here's an example of three properties using variable delay.
```python
class Main(m.Circuit):
    io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
    # SVA
    f.assert_(f.sva(io.write, "|-> ##[1:2]", io.read),
              on=f.posedge(io.CLK))
    f.assert_(f.sva(io.write, "|-> ##[*]", io.read),
              on=f.posedge(io.CLK))
    f.assert_(f.sva(io.write, "|-> ##[+]", io.read),
              on=f.posedge(io.CLK))
    # Infix
    f.assert_(io.write | f.implies | f.delay[1:2] | io.read,
              on=f.posedge(io.CLK))
    f.assert_(io.write | f.implies | f.delay[0:] | io.read,
              on=f.posedge(io.CLK))
    f.assert_(io.write | f.implies | f.delay[1:] | io.read,
              on=f.posedge(io.CLK))
```

## Repetition and Sequences
Here's an example of using repetition and sequences.  Note the use of
`f.sequence` in order to group sequences together for the repeition operator.

This property waits for read and write to be low for 2 cycles, followed by seq0
(read low, then write high) repeated twice followed by seq1 (read high, write
high).
```python
class Main(m.Circuit):
    io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
    # SVA
    seq0 = f.sequence(f.sva(~io.read, "##1", io.write))
    seq1 = f.sequence(f.sva(io.read, "##1", io.write))
    f.assert_(f.sva(~io.read & ~io.write, "[*2] |->", seq0,
                    f"[*2] ##1", seq1), on=f.posedge(io.CLK))
    # Infix
    seq0 = f.sequence(~io.read | f.delay[1] | io.write)
    seq1 = f.sequence(io.read | f.delay[1] | io.write)
    f.assert_(~io.read & ~io.write | f.repeat[2] | f.implies | seq0 |
              f.repeat[2] | f.delay[1] | seq1, on=f.posedge(io.CLK))
```

# Coverage
Fault provides a function `f.cover` that uses the same interface as
`f.assert_`.  This will generate a system verilog coverage statement.
In order to use this, you'll need to compile_and_run your circuit with
`coverage=True` (NOTE: `vcs` is currently unsupported, please open an issue to
request support).

Here's an example:
```python
def test_coverage(capsys):
    """
    NOTE: Uses pytest's capsys feature to check the output of stdout
    """
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit)) + m.ClockIO()
        io.O @= m.Register(T=m.Bit)()(io.I)
        f.cover(io.I | f.delay[1] | ~io.I, on=f.posedge(io.CLK))
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True},
                           disp_type="realtime", coverage=True)

    out, _ = capsys.readouterr()
    # not covered
    assert """\
  Disabled Finish Failed   Assertion Name
         0      0      0   Main_tb.dut.__cover1
  Total Assertions = 1,  Failing Assertions = 0,  Unchecked Assertions = 1\
""" in out
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 0
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True},
                           disp_type="realtime", coverage=True)

    out, _ = capsys.readouterr()
    # covered
    assert """\
  Disabled Finish Failed   Assertion Name
         0      1      0   Main_tb.dut.__cover1
  Total Assertions = 1,  Failing Assertions = 0,  Unchecked Assertions = 0\
""" in out
```
