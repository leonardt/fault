# assert_immediate, assert_final, and assert_initial

`fault` provides the ability to define immediate assertions using the
`assert_immediate` function.  These assertions are expected to hold true
throughout the entire simulation.  

There are also the two variants:
* `assert_final`: holds true at the end of simulation
* `assert_initial`: holds true at the beginning of simulation

Here is the interface (`assert_final` and `assert_initial` share the same interface):
```python
def assert_immediate(cond, success_msg=None, failure_msg=None, severity="error",
                     on=None, name=None):
    """
    cond: m.Bit
    success_msg (optional): passed to $display on success
    failure_msg (optional): passed to else $<severity> on failure (strings are
                            wrapped in quotes, integers are passed without
                            quotes (for $fatal))
    severity (optional): "error", "fatal", or "warning"
    name (optional): Adds `{name}: ` prefix to assertion
    compile_guard (optional): a string or list of strings corresponding to
                              macro variables used to guard the assertion with
                              verilog `ifdef statements
    """
```

Here is an example that will fail when run:
```python
class Foo(m.Circuit):
    io = m.IO(
        I0=m.In(m.Bit),
        I1=m.In(m.Bit)
    )
    f.assert_immediate(~(io.I0 & io.I1), failure_msg="Failed!")

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

## Display Values on Failure
The `assert_immediate` `failure_msg` parameter can accept a tuple of the form `("<display message>", *display_args)`.  This is useful for displaying debug information upon an assertion failure.  Here is an example:
```python
class Foo(m.Circuit):
    io = m.IO(
        I0=m.In(m.Bit),
        I1=m.In(m.Bit)
    )
    f.assert_immediate(
        io.I0 == io.I1,
        failure_msg=("io.I0 -> %x != %x <- io.I1", io.I0, io.I1)
    )

tester = f.Tester(Foo)
tester.circuit.I0 = 1
tester.circuit.I1 = 0
tester.eval()
tester.compile_and_run("verilator", magma_opts={"inline": True},
                       flags=['--assert'])
````

This produces the error message:
```
%Error: Foo.v:29: Assertion failed in TOP.Foo: io.I0 -> 1 != 0 <- io.I1
```
