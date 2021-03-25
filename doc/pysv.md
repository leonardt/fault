# pysv Integration
fault provides integration with the [pysv](https://github.com/kuree/pysv)
package which allows test benches to call Python functions and use Python
classes (with limitations).  `pysv` generates a C++ wrapper around marked
Python code that can then be invoked via the SystemVerilog DPI.  `fault`
provides tester actions that allow for the invocation of the `pysv` code in a
generated test bench.

Be sure to check the pysv
[documentation](https://pysv.readthedocs.io/?badge=latest) for any questions
related to using the package and use [GitHub
repo][https://github.com/Kuree/pysv] for issues.

## Functions
To use a Python function in our simulation, we wrap it with the `@pysv.sv`
decorator and optionally specify the input and return datatypes.  The supported
types are listed
[here](https://github.com/Kuree/pysv/blob/master/pysv/types.py) and correspond
 to SystemVerilog types.  If a type is not provided, a default type of `Int` will be used.

Here's an example:
```python
import pysv

@pysv.sv(a=pysv.DataType.UByte, b=pysv.DataType.UByte,
         return_type=pysv.DataType.UByte)
def byte_add(a, b):
    return a + b
```

To invoke this function in a test bench, we use the `teseter.make_call_expr` function.

```python
tester.expect(tester.circuit.O,
              tester.make_call_expr(gold_func, tester.circuit.A,
                                    tester.circuit.B))
```

This creates an expression that calls the Python function with the *peeked*
values of the A and B ports and returns the result of the function (which is
then used to expect the output value of the circuit).

## Classes
`pysv` provides support for interacting with Python classes.  It's important to note that this integration will instantiate the class at test bench runtime.  This means that passing data from the test bench generator code to the runtime Python code is non-trivial.

Here's a simple example of a class definition using `pysv`

```python
class Model:
    @pysv.sv(b=pysv.DataType.UByte)
    def __init__(self, b):
        self.b = b

    @pysv.sv(a=pysv.DataType.UByte)
    def add(self, a):
        return a + self.b

    @pysv.sv()
    def incr(self, amount):
        self.b += amount
```

To use this class, we must first create an instance.  This can be done by assigning a *call expression* of the class (i.e. initialize the object) to a variable with the class as a type.  Here's an example:

```python
model = tester.Var("model", Model)
tester.poke(model, tester.make_call_expr(Model, 1))
```

Notice we can pass basic arguments to the `Model` constructor (in this case, an integer value 1).  `pysv` supports more complex arguments such as other Python classes, but this has not been tested.  Please open a GitHub issue to request the feature (ideally with an example code snippet of what you'd like to do).

With an instance of the Python class, we can now invoke the various methods during test bench execution, for example:
```python
loop = tester.loop(10)
loop.poke(tester.circuit.B, loop.index)
loop.eval()
loop.expect(tester.circuit.O, tester.make_call_expr(model.add, loop.index))

tester.make_call_stmt(model.incr, BitVector[32](2))

tester.expect(tester.circuit.O, tester.make_call_expr(model.add, 9) - 2)
```

Notice here that we make use of the `make_call_stmt` action which is similar to `make_call_expr` except that the return value is discarded (useful in the case of methods that update internal state of the object but do not return any values).  

## Monitors
A useful pattern is to have a Python object *monitoring* a circuit.  In *fault*, a monitor is used with `SynchronousTester` and samples the input and output values of a circuit each cycle.  This allows the object to track the inputs and outputs of the circuit, update internal state, and check assertions.

Here's an example of a Monitor:
```python
@fault.python_monitor()
class Monitor(fault.PysvMonitor):
    @sv()
    def __init__(self):
        self.value = None

    @sv()
    def observe(self, A, B, O):
        print(A, B, O, self.value)
        if self.value is not None:
            assert O == self.value, f"{O} != {self.value}"
        self.value = BitVector[4](A) + BitVector[4](B)
        print(f"next value {self.value}")
```
Note that we use the `fault.python_monitor` decorator on the class which is necessary for the insertion of wrapper code that handles data type conversion.  The reason will be shown in the next example.

A `python_monitor` defines an `observe` method which references ports on the circuit.  In this case, a circuit has inputs `A` and `B` and an output `O`.  The monitor stores the value of adding `A` and `B` in an internal variable, and uses the previous value of the internal variable to check the value of `O` (modeling a simple registered output).

To use this monitor in the test bench, we simply create a variable and then call the `attach_monitor` function.  Then, any calls to `advance_cycle` will insert invocations of the monitor.  Here's an example:
```python
tester = fault.SynchronousTester(circuit)
# NOTE: Fault initializes the clock to 0, for the monitor logic to work
# correctly, the clock must be started at 1
tester.poke(circuit.CLK, 1)
monitor = tester.Var("monitor", Monitor)
tester.poke(monitor, tester.make_call_expr(Monitor))
tester.attach_monitor(monitor)

for i in range(4):
    tester.poke(tester.circuit.A, BitVector.random(4))
    tester.poke(tester.circuit.B, BitVector.random(4))
    tester.advance_cycle()  # Monitor invoked implicitly here for each input
```

`fault` supports the mapping of SystemVerilog types to Magma types for testing (e.g. magma Product types are flattened into individual ports, but we can reconstruct these in Python when using them in a monitor).  If you'd like to request this feature for generic functions/classes, please open an issue and we will add it.  Here's an example of an `observe` method that takes a Product type as an argument:

```python
class T(m.Product):
    A = m.In(m.Bits[4])
    B = m.In(m.Bits[4])

@fault.python_monitor()
class ProductMonitor(fault.PysvMonitor):
    @sv()
    def __init__(self):
        self.value = None

    @sv()
    def observe(self, I: T, O):
        if self.value is not None:
            assert O == self.value, f"{O} != {self.value}"
        self.value = BitVector[4](I.A) + BitVector[4](I.B)
        print(f"next value {self.value}")
```

Note that we must annotate the type of the input `I` with `T` which must be the same type as the corresponding circuit port.  Then, we can use dot notation (e.g. `I.A`) to refer to the product fields.  This also works for magma arrays and tuples.

## Drivers
Support for Python drivers similiar to the monitors shown in the previous section is forthcoming.  Please open a GitHub issue to request it!

## Full Code Examples
The snippets of code used in this document were taken from this [test file](https://github.com/leonardt/fault/blob/master/tests/test_pysv.py).  Sometimes it can be useful to see the full code (e.g. the circuits being tested).  Please open an issue if you find that the document has become out of date with the test code, and we will update it.