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

# SVA 
Use the `f.sva` function to construct sva properties by interleaving magma
signal/expressions and SVA operators. Here's a simple example:
```python
f.assert_(f.sva(io.I, "|-> ##1", io.O.value() == 0),
          on=f.posedge(io.CLK))
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
