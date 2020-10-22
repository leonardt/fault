# assert_immediate

`fault` provides the ability to define immediate assertions using the `assert_immediate` function.

Here is the interface:
```python
def assert_immediate(cond, success_msg=None, failure_msg=None, severity="error",
                     on=None):
    """
    cond: m.Bit
    success_msg (optional): passed to $display on success
    failure_msg (optional): passed to else $<severity> on failure (strings are
                            wrapped in quotes, integers are passed without
                            quotes (for $fatal))
    severity (optional): "error", "fatal", or "warning"
    on (optional): If None, uses always @(*) sensitivity, otherwise something
                   like f.posedge(io.CLK)
    """
```

Here is an example that will fail when run:
```python
class Foo(m.Circuit):
    io = m.IO(
        I0=m.In(m.Bit),
        I1=m.In(m.Bit)
    )
    f.assert_immediate(~(io.I0 & io.I1),
                       success_msg=success_msg,
                       failure_msg=failure_msg,
                       severity=severity)

tester = f.Tester(Foo)
tester.circuit.I0 = 1
tester.circuit.I1 = 1
tester.eval()
tester.compile_and_run("verilator", magma_opts={"inline": True},
                       flags=['--assert'])
```

If we change the input values, it will pass:
```python
tester = f.Tester(Foo)
tester.circuit.I0 = 0
tester.circuit.I1 = 1
tester.eval()
tester.compile_and_run("verilator", magma_opts={"inline": True},
                       flags=['--assert'])
```
