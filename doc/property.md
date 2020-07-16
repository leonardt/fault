**NOTE** Property support is experimental, please submit bug reports and
feature requests via GitHub Issues.

Fault provides two interfaces for defining temporal assertions.  The firt uses
a magic implementation of the `__or__` and `__ror__` methods to define custom
"infix" operators.  The second provides an interface to provide strings
containing SVA operator syntax.
# Infix Operator Interface
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
## Basic assertion

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
