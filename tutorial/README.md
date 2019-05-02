Welcome to the **fault tutorial**. The sources for these files are hosted in
the [GitHub
repository](https://github.com/leonardt/fault/tree/master/tutorial), please
submit issues using the [GH issue
tracker](https://github.com/leonardt/fault/issues).  Pull requests with typo
fixes and other improvements are always welcome!

Section 1 provides an introduction to using the fault system including a set of
examples and exercises and is intended to be read by those interested in using
the fault system.  Section 2 provides an overview of the fault system
architecture as well as a roadmap and is intended to be read by those
interested in contributing to the fault source code.

# Table of Contents
<!-- generated using https://github.com/jonschlinkert/markdown-toc -->

<!-- toc -->

- [Section 1: Testing Hardware Circuits using Fault](#section-1-testing-hardware-circuits-using-fault)
  * [Installation](#installation)
    + [Python 3.7.2](#python-372)
      - [MacOS](#macos)
      - [Linux](#linux)
    + [Using pip](#using-pip)
    + [From source](#from-source)
  * [Overview](#overview)
  * [Tester Abstraction](#tester-abstraction)
    + [Tester Actions](#tester-actions)
      - [Poke](#poke)
      - [Eval](#eval)
      - [Expect](#expect)
    + [Executing Tests](#executing-tests)
    + [Exercise 1](#exercise-1)
  * [Extending The Tester Class](#extending-the-tester-class)
    + [Exercise 2](#exercise-2)
  * [pytest Parametrization](#pytest-parametrization)
    + [Exercise 3](#exercise-3)
  * [Assume/Guarantee](#assumeguarantee)
    + [Constrained Random](#constrained-random)
    + [Formal Verification](#formal-verification)
    + [Exercise 4](#exercise-4)
- [Section 2: Fault Internals](#section-2-fault-internals)
  * [Testers](#testers)
    + [SymbolicTester](#symbolictester)
    + [FunctionalTester](#functionaltester)
  * [Targets](#targets)
    + [VerilogTarget](#verilogtarget)
    + [VerilatorTarget](#verilatortarget)
    + [SystemVerilogTarget](#systemverilogtarget)
    + [CoSA](#cosa)
  * [Roadmap](#roadmap)
    + [Simulation Actions](#simulation-actions)
      - [Loops](#loops)
      - [File IO](#file-io)
      - [Monitors](#monitors)
    + [Constrained Random](#constrained-random-1)
    + [Formal](#formal)

<!-- tocstop -->

# Section 1: Testing Hardware Circuits using Fault
This section provides an introduction to using the `fault` system to
meta-program hardware test generators.

## Installation
### Python 3.7.2

Magma requires Python 3.7.2.
If you don't have Python setup, we recommend using Miniconda

#### MacOS
```
$ wget https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
$ bash Miniconda3-latest-MacOSX-x86_64.sh
```

#### Linux
```
$ wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
$ bash Miniconda3-latest-Linux-x86_64.sh
```

Follow the prompts to install Miniconda and add Python to your PATH:

```
...
Please, press ENTER to continue
>>> [ENTER]
...
<scroll down>
...
Do you accept the license terms? [yes|no]
[no] >>> yes
...
   - Press ENTER to confirm the location
   - Press CRTL-C to abort the installation
   - Or specify a different location below

[/Users/yourusername/miniconda3] >>> [ENTER]
...
Do you wish the installer to prepend the Miniconda3 install location
to PATH in your /Users/yourusername/.bash_profile ? [yes|no]
[yes] >>> yes
```

### Using pip
The simplest way to get started for this tutorial is to install fault, magma,
and mantle using `pip`.

```
pip install fault magma-lang mantle
```

### From source
You can also install the packages directly from the GitHub repository to access
the bleeding edge versions.  This provides faster access to new features and
bug fixes, but the code is less stable than the releases.
```
git clone https://github.com/leonardt/fault
cd fault && pip install -e . && cd ..
git clone https://github.com/phanrahan/magma
cd magma && pip install -e . && cd ..
git clone https://github.com/phanrahan/mantle
cd mantle && pip install -e . && cd ..
```

## CoreIR
Follow the instructions at
https://github.com/rdaly525/coreir/blob/master/INSTALL.md (skip the Python
bindings because those are installed by pip automatically)

## Overview
The *fault* library abstracts circuit testing actions using Python objects.

Underlying the fault framework is
[magma](https://github.com/phanrahan/magma), a library that abstracts circuits
as Python objects.  Magma provides the ability to define circuits in Python,
wrap existing circuits from `verilog`, or create designs combining both.
Fault's features are agnostic to how the `magma.Circuit` object is defined,
which means that you can use it with your existing `verilog` designs by using
magma's `DefineFromVerilog` feature.

Fault is designed as an embedded DSL to enable the construction of *test
generators* using standard Python programming techniques.  A *test generator*
is a program that consumes a set of parameters to produce a test or suite of
tests for a specific instance of a *chip generator*.  A *chip generator* is a
program that consumes a set of parameters to produce a *chip* (an instance of
the chip generator).  

As an embedded DSL, fault enables users to leverage techniques including OOP
(object-oriented programming) and metaprogramming to construct flexible,
composable, and reuseable tests.  Furthermore, fault users are able to leverage
the large ecosystem of Python libraries including the [pytest
framework](https://pytest.org/).

An important design goal of fault is to provide a unified interface for
describing circuit test components that can be used in multiple test
environments including simulation, formal methods, emulation, and silicon.
By providing a shared environment 
Fault provides the ability to easily reuse test components across these
environments.

## Tester Abstraction

The `fault.Tester` object is the main entity provided by the fault library.  It
provides a mechanism for recording a set of test actions performed on a magma
circuit.  Full documentation can be found at
http://truong.io/fault/tester.html.  A `Tester` must be instantiated with one
argument `circuit` which corresponds to a `magma.Circuit` class that will be
tested.   Here's a simple example:

```python
import magma as m
import fault


class Passthrough(m.Circuit):
    IO = ["I", m.In(m.Bit), "O", m.Out(m.Bit)]

    @classmethod
    def definition(io):
        io.O <= io.I


passthrough_tester = fault.Tester(Passthrough)
```

There is a second optional argument `clock` which corresponds to a port on
`circuit` to be used by the `step` action (described in more detail later).
Here's an example:

```python
import magma as m
import mantle
import fault


class TFF(m.Circuit):
    IO = ["O", m.Out(m.Bit), "CLK", m.In(m.Clock)]

    @classmethod
    def definition(io):
        reg = mantle.Register(None, name="tff_reg")
        reg.CLK <= io.CLK
        reg.I <= ~reg.O
        io.O <= reg.O


tff_tester = fault.Tester(TFF, clock=TFF.CLK)
```

### Tester Actions
The `Tester` class provides facilities to perform various testing *actions*.
These actions are recorded by the object and used when compiling to a test
execution target.  It is important to understand the staged metaprogramming
architecture underlying the fault system. That is, fault tests are executed in
at a different stage than when they are specified. This allows the users to
metaprogram the description of test (stage 1), then execute the metaprogrammed
test (stage 2).

#### Poke
With an instance of a `fault.Tester` object, you can now perform actions to
verify your circuit.  The first actions introduced are `poke`, `eval`, and
`expect`.  

The `poke` action is performed by setting an attribute on the `fault.Tester`
instance's `circuit` attribute.  Here's an example using the
`passthrough_tester`:

```python
passthrough_tester.circuit.I = 1
```

The `poke` (`setattr`) pattern supports poking internal instances of the
`mantle.Register` circuit using the `value` attribute. This can be done at
arbitrary depths in the instance hierarchy.  An instance can be referred to as
an attribute of the top level `circuit` attribute or as an attribute of a
nested instance. Here's an example using the `tff_tester`:

```python
tff_tester.circuit.reg.tff_reg.value = 1
```

Poking internal ports for wrapped verilog modules is more involved and is
documented here for those who need it:
https://github.com/leonardt/fault/blob/master/doc/actions.md#wrappedveriloginternalport.

#### Eval
The `eval` action is performed by calling the `eval` method on a `fault.Tester`
instance.  This action triggers an evaluation of the circuit when a test is run
using cycle-accurate simulation, where multiple `poke` actions can be recorded
before a circuit is evaluated. It has no effect for event-based simulations
where *eval* is implicitly called after every `poke` action.  Here's an example:
```python
passthrough_tester.circuit.I = 0
passthrough_tester.eval()
# Passthrough.O should be 0
passthrough_tester.circuit.I = 1
# Passthrough.O should still be 0 because `eval` has not be called yet
passthrough_tester.eval()
# Passthrough.O should be 1
```

#### Expect
The `expect` action is used to verify the value of output ports.  Expect is
called as a method on attributes retrieved from the `circuit` attribute of a
`fault.Tester` instance.  Here's an example:
```python
passthrough_tester.circuit.I = 1
passthrough_tester.eval()
passthrough_tester.circuit.O.expect(1)
```

#### Step
The `step` action is used to step the `clock` port provided to the `__init__`
function.  The semantics are equivalent to:
```python
tester.eval()
for i in range(n_step):
    tester.circuit.CLK ^=1  # invert the clock
    tester.eval()           # evaluate the circuit
```

### Executing Tests
Once you have finished recording your test actions, it is now time to run the
test.  This is done using the `compile_and_run` method of the tester instance.
Here are three examples:

```python
passthrough_tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")
passthrough_tester.compile_and_run("system-verilog", simulator="ncsim", directory="build")
passthrough_tester.compile_and_run("system-verilog", simulator="vcs", directory="build")
```

The first argument, `target`, is required and corresponds to a string selecting
the desired test execution target.  Valid targets are `"verilator"` and
`"system-verilog"`. When using the `"system-verilog"` target, one should also
specify a simulator, either `"ncsim"` or `"vcs"`.  Other arguments are target
dependent, more information can be found in the API documentation for each
target (keyword arguments to the `compile_and_run` method are passed through to
the `__init__` method of the selected target):
* [`SystemVerilogTarget.__init__`](http://truong.io/fault/system_verilog_target.html#fault.system_verilog_target.SystemVerilogTarget.__init__)
* [`VerilatorTarget.__init__`](http://truong.io/fault/verilator_target.html#fault.verilator_target.VerilatorTarget.__init__)

### Exercise 1
Suppose you had the following definition of a simple, configurable ALU in magma
(source: [fault/tutorial/exercise_1.py](./exercise_1.py)):
```python
import magma as m
import mantle


class ConfigReg(m.Circuit):
    IO = ["D", m.In(m.Bits[2]), "Q", m.Out(m.Bits[2])] + \
        m.ClockInterface(has_ce=True)

    @classmethod
    def definition(io):
        reg = mantle.Register(2, has_ce=True, name="config_reg")
        io.Q <= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    IO = ["a", m.In(m.UInt[16]),
          "b", m.In(m.UInt[16]),
          "c", m.Out(m.UInt[16]),
          "config_data", m.In(m.Bits[2]),
          "config_en", m.In(m.Enable),
          ] + m.ClockInterface()

    @classmethod
    def definition(io):
        opcode = ConfigReg(name="opcode_reg")(io.config_data, CE=io.config_en)
        io.c <= mantle.mux(
            [io.a + io.b, io.a - io.b, io.a * io.b, io.b - io.a], opcode)
```

Study the implementation so you understand how it works (ask for help if you
don't!). Then, write a fault test which checks the functionality of each op in
the ALU.  You should construct two variants of your test, one that uses the
configuration interface (the `config_data` and `config_en` ports) and another
that exercises the ability to the poke the internal `config_reg` register.  You
may find the function `fault.random.random_bv(width)`, which returns a random
`hwtypes.BitVector` of a specified `width`, useful.

## Extending The Tester Class

The `fault.Tester` class can be extended using the standard Python subclassing
pattern.  Here's an example that defines a `ResetTester` which exposes a
`reset` method:
```python
class ResetTester(fault.Tester):
    def __init__(self, circuit, clock, reset_port):
        super().__init__(circuit, clock)
        self.reset_port = reset_port

    def reset(self):
        self.poke(self.reset_port, 1)
        self.eval()
        self.poke(self.reset_port, 0)
        self.eval()
```

Notice that the `reset` method implementation uses the action method API (i.e.
`self.poke`) rather than the `setattr`/`getattr` based interface described
before.  This pattern is useful for writing generic `Tester`s parametrized over
ports.  More information about the action method API interfaces can be found in
the [Tester documentation](http://truong.io/fault/tester.html).

Defining methods on a `Tester` subclass allows you to use the UVM driver
pattern to lower high-level API calls into low-level port values.  It also
allows you construct reuseable test components that can be composed using the
standard inheritance pattern.  Here's an example of composing a driver for a
configuration bus with the reset tester:
```python
class ConfigurationTester(Tester):
    def __init__(self, circuit, clock, config_addr_port, config_data_port,
                 config_en_port):
        super().__init__(circuit, clock)
        self.config_addr_port = config_addr_port
        self.config_data_port = config_data_port
        self.config_en_port = config_en_port

    def configure(self, addr, data):
        self.poke(self.clock, 0)
        self.poke(self.config_addr_port, addr)
        self.poke(self.config_data_port, data)
        self.poke(self.config_en_port, 1)
        self.step(2)
        self.poke(self.config_en_port, 0)


class ResetAndConfigurationTester(ResetTester, ConfigurationTester):
    def __init__(self, circuit, clock, reset_port, config_addr_port,
                 config_data_port, config_en_port):
        # Note the explicit calls to `__init__` to manage the multiple
        # inheritance, rather than the standard use of `super`
        ResetTester.__init__(self, circuit, clock, reset_port)
        ConfigurationTester.__init__(self, circuit, clock, config_addr_port,
                                     config_data_port, config_en_port)
```

### Exercise 2
Suppose you have the following two memory modules defined in magma (source:
[fault/tutorial/exercise_2.py](./exercise_2.py)):
```python
import magma as m
import mantle
import fault


data_width = 16
addr_width = 4

# Randomize initial contents of memory
init = [fault.random.random_bv(data_width) for _ in range(1 << addr_width)]


class ROM(m.Circuit):
    IO = [
        "RADDR", m.In(m.Bits[addr_width]),
        "RDATA", m.Out(m.Bits[data_width]),
        "CLK", m.In(m.Clock)
    ]

    @classmethod
    def definition(io):
        regs = [mantle.Register(data_width, init=int(init[i]))
                for i in range(1 << addr_width)]
        for reg in regs:
            reg.I <= reg.O
        io.RDATA <= mantle.mux([reg.O for reg in regs], io.RADDR)


class RAM(m.Circuit):
    IO = [
        "RADDR", m.In(m.Bits[addr_width]),
        "RDATA", m.Out(m.Bits[data_width]),
        "WADDR", m.In(m.Bits[addr_width]),
        "WDATA", m.In(m.Bits[data_width]),
        "WE", m.In(m.Bit),
        "CLK", m.In(m.Clock),
        "RESET", m.In(m.Reset)
    ]

    @classmethod
    def definition(io):
        regs = [mantle.Register(data_width, init=int(init[i]), has_ce=True,
                                has_reset=True)
                for i in range(1 << addr_width)]
        for i, reg in enumerate(regs):
            reg.I <= io.WDATA
            reg.CE <= (io.WADDR == m.bits(i, addr_width)) & io.WE
        io.RDATA <= mantle.mux([reg.O for reg in regs], io.RADDR)
```

First, define a subclass `ReadTester` of `fault.Tester` that provides an
`expect_read` method which takes in two parameters `addr` and `value`. The
method should use the address `addr` to perform a read operation and check that
the result is equal to `value`.  Use `ReadTester` to test both the `ROM` and
the `RAM`.

Next, extend `ReadTester` with a subclass `ReadAndWriteTester` that adds a
`write` method which takes in an `addr` and `value` parameter. Use the
`ReadAndWriteTester` to test the functionality of the `RAM`.

Finally, compose your newly defined testers with the provided `ResetTester`
(from [fault/tutorial/reset_tester.py](./reset_tester.py)) to create a
`ROMTester` and `RAMTester`.  Port your previous tests to use these new testers
and extend them to also check that the reset logic behaves as expected.

## pytest Parametrization
This section assumes basic knowledge of the `pytest` framework, please review
[the pytest
documentation](https://docs.pytest.org/en/latest/getting-started.html) if
you're unfamiliar or need a refresher.

The pytest framework provides powerful features for parametrizing tests. Using
this pattern greatly improves the user experience when working with
parametrized tests, including more informative error messages and facilities to
rerun tests with specific parameters.  Full documentation on pytest
parametrization can be found
[here](https://docs.pytest.org/en/latest/parametrize.html).

Suppose you had the following `pytest` function which runs your `SimpleALU`
test from exercise 1:
```python
def test_simple_alu():
    <SimpleALU Test Code>
```

If `SimpleALU` had a bug in one of the operations, when running the test you
would see something along the lines of:
```

====================================== FAILURES =======================================
___________________________________ test_simple_alu ___________________________________

    def test_simple_alu():
        ...
>       tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")

...

Got      : 0x1
Expected : 0xffff
i        : 13
Port     : SimpleALU.c
========================= 1 failed, 6 passed in 13.23 seconds =========================
```

The key problem here is that it's not clear which operation failed. You can try
this out by changing one of the operations in `SimpleALU`, for example, swap
the `+` operator to `^` and run your test.

We can use pytest's parametrization feature to parametrize the test over the
operation, which greatly improves the readability of the failure log, and
provides an easy mechanism for re-running the test just for the specific
operation of interest. Here's an example that passes an enumerated list of
operation strings. The index of the operation is used as the opcode, and the
string is used to grab an operator from the built-in Python `operator` module.

```python
@pytest.mark.parametrize("opcode, op",
                         enumerate(["add", "sub", "mul", "floordiv"]))
def test_simple_alu_parametrized(opcode, op):
    op = getattr(operator, op)
    <Test code referring to `op`>
```

Now, when a specific operation fails, you'll see an output along the lines of:
```

====================================== FAILURES =======================================
_________________________ test_simple_alu_parametrized[1-sub] _________________________

opcode = 1, op = <built-in function sub>

    @pytest.mark.parametrize("opcode, op",
                             enumerate(["add", "sub", "mul", "floordiv"]))
    def test_simple_alu_parametrized(opcode, op):
        op = getattr(operator, op)
        ...

>       tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")

...

Got      : 0xffff
Expected : 0x1
i        : 7
Port     : SimpleALU.c
========================= 1 failed, 6 passed in 13.09 seconds =========================
```
Notice that the report clearly shows which operation failed by including the
parameters in the test name `test_simple_alu_parametrized[1-sub]`.  You can use
this parametrized name to rerun this specific test with `pytest -k
test_simple_alu_parametrized[1-sub]` (for zsh users, you'll need to enclose the
name in a string or escape the square brackets). More on the `-k` flag can be
found
[here](https://docs.pytest.org/en/latest/example/markers.html#using-k-expr-to-select-tests-based-on-their-name).

### Exercise 3
Refactor your `SimpleALU` test from exercise 1 to use the `parametrize` pattern
for the `opcode`, `op`, and the two data inputs `a, b`.  Then, play around with
the `SimpleALU` definition by injecting various bugs to observe how the pytest
failures are reported.  For example, if you change one of the operations to a
different function, the test failures should clearly indicate which operation
has been changed.  As another example, suppose one operation only failed for
specific values (e.g. negative values), then the test reports should give a
hint to this (assuming you've parametrized your inputs in a way that tests
these faulty values!).

## Assume/Guarantee
The assume/guarantee interface provides a unified abstraction for describing
constrained random and formal method based tests.  An *assumption* is an
assertion on the values of the input ports of the circuit under test.  A
*guarantee* is an assertion on the values of the output ports of a circuit
under test.  

### Constrained Random
For constrained random verification, assumptions are used to generate input
stimuli for the circuit under test.  The current implementation uses
assumptions as predicates to filter out valid values from a random number
stream.  Guarantees are translated into code in the target language (i.e. C++
for verilator, SystemVerilog for ncsim/vcs) that is run every time `eval` is
called.  For example, if you perform a guarantee action that states that an
output must be positive, every time an `eval` action occurs, this guarantee is
checked by reading the output and running the code describing the guarantee.

Here's an example of using the assume/guarantee interface for constrained
random verification:
```python
symbolic_tester = fault.SymbolicTester(SimpleALU, SimpleALU.CLK, num_tests=100)
symbolic_tester.circuit.config_en = 1
symbolic_tester.circuit.config_data = 0
symbolic_tester.step(2)
symbolic_tester.circuit.config_en = 0
symbolic_tester.step(2)
symbolic_tester.circuit.opcode_reg.Q.expect(0)
symbolic_tester.circuit.a.assume(lambda a: a < BitVector(32768, 16))
symbolic_tester.circuit.b.assume(lambda b: b < BitVector(32768, 16))
symbolic_tester.circuit.c.guarantee(lambda a, b, c: (c >= a) and (c >= b))
```

First, notice that the assume/guarantee interface can be combined with the poke
and step actions. This allows the user to setup the state of the circuit under
test.  In this example, this corresponds to configuring the register holding
opcode to the desired operation of interest (0 for add).  Then, the test
assumes that the inputs `a, b` are both values smaller than 32768 (which is `1
<< 15`).  Given these assumptions, the test guarantees that the output value
`c` is greater than both `a` and `b` (since `c` is a 16-bit value and `a + b`
cannot overflow given the assumptions).  The `num_tests` parameter used to
initialize the `SymbolicTester` corresponds to the number of constrained random
input stimuli to check.

Here's how we can run the test using verilator:
```python
symbolic_tester.compile_and_run(
    "verilator", flags=["-Wno-fatal"], magma_opts={"verilator_debug": True}
)
```

### Formal Verification
For formal verification, assumptions are provided to the formal checker as
properties that can be assumed to be true. Guarantees are provided as
properties to be proven to be true.  The current implementation translates the
Python specification of these properties into the format used by the [CoSA
tool](https://github.com/cristian-mattarei/CoSA).

We can run the same example used for constrained verification of the
`SimpleALU` using CoSA by changing the `compile_and_run` target.
```python
symbolic_tester.compile_and_run(
    "cosa", magma_opts={"passes": ["rungenerators", "flatten", "cullgraph"]}
)
```

Note that CoSA requires the coreir generated by magma to be flattened, which we
achieve by using the `"passes"` option.  We also cull the graph to remove any
unused modules.

### Exercise 4
Use the assume/guarantee interface to develop a set of tests for the `ROM` and
`RAM` used in exercise 2.  Run your tests using the constrained random target
(verilator) and the formal target (cosa) and observe the performance (which one
is faster?) as well as the readability of the output (is it easy to understand
why a test fails when it does?).  An example of a simple test would be to set
the write enable on the `RAM`, assume that the write address input of the
memory is in a certain range of values, assume that the read address is not in
the same range as the write address, and then guarantee that the value of the
read data output is equal to the corresponding value for the read address in
the initial contents of the memory (that is, the initial contents should not
have been overwritten).  It's important to remark that fault only supports the
specification of *combinational* properties, adding support for the
specification of temporal properties (ala LTL) is on the roadmap.

## More Examples
Armed with your understanding of fault, you should now be able to look at more
complex examples of fault tests from real code bases. Here are some places to check
out:
* [canal](https://github.com/rsetaluri/canal/tree/master/tests)
* [garnet](https://github.com/StanfordAHA/garnet/tree/master/tests)
* [gemstome](https://github.com/rsetaluri/gemstone/blob/master/gemstone/common/testers.py)

# Section 2: Fault Internals
This section provides an introduction to the internal architecture of the fault
system.  The goal is to provide the required knowledge for anyone interested in
contributing bug fixes, features, or refactors to the fault codebase.  The
fault API docs are hosted at
[http://truong.io/fault/](http://truong.io/fault/), this is a valuable link to
remember.

## Testers

The `fault.Tester` class is the core entity that provides the testing
abstractions.  Users instance a `Tester` object and use the API to record test
actions, compile an action sequence to a concrete test harnesses for a specific
target, and run the generated test harness.  The API documentation can be found
at http://truong.io/fault/tester.html.  The source code can be found
https://github.com/leonardt/fault/blob/master/fault/tester.py.  

Those interested in adding new user facing features to fault will likely add
them to the tester API (e.g. adding a new action).  Those wishing to extend
fault with new targets should look at the `make_target` method.  More details
on targets will be discussed later.

The `circuit` property method returns a `CircuitWrapper` instance which is used
to implement the `setattr`/`getattr` interface for `poke` and `expect` actions. 
The core logic for this is defined in
hgttps://github.com/leonardt/fault/blob/master/fault/wrapper.py.

Fault provides two standard extensions to the `Tester` class: the
`SymbolicTester` and the `FunctionalTester`.

### SymbolicTester
The source code for the `SymbolicTester` can be found in
https://github.com/leonardt/fault/blob/master/fault/symbolic_tester.py

This tester extends the `__init__` method to accept a parameter for the number
of tests to run (for constrained random) and adds the `assume`/`guarantee`
methods for recording assumptions and guarantees.

### FunctionalTester
The source code for the `FunctionalTester` can be found in
https://github.com/leonardt/fault/blob/master/fault/functional_tester.py

This Tester provides a convenience mechanism for verifying a DUT against a
functional model.  The basic pattern is that every time `eval` is invoked on
the Tester, a check is done to verify that the current outputs of the
functional model are equivalent to the outputs of the DUT.  This pattern works
best with a model that is fairly low-level (e.g. cycle accurate). The user has
the flexibility to relax accuracy of the model by setting the outputs of the
functional model to be `fault.AnyValue`.  Anything is equal to
`fault.AnyValue`, so the user can manage when to actually perform the
consistency check by only updating `fault.AnyValue` at the appropriate time.

## Targets
A `fault.Target` is an abstract base class defined in
https://github.com/leonardt/fault/blob/master/fault/target.py

Currently it only requires that a concrete subclass implement the `run` method
which corresponds to running a test with a specific sequence of actions. 

### VerilogTarget
The `VerilogTarget` is a parent class shared by both the `Verilator` and
`SystemVerilog` targets.  The source code can be found in
https://github.com/leonardt/fault/blob/master/fault/verilog_target.py

It provides common functionality for generating Verilog code for actions and
requires that subclasses implement the specific `make_<action>` method for each
action.  The `__init__` method compiles the circuit into verilog using magma.

### VerilatorTarget
The source code for the `VerilatorTarget` can be found in
https://github.com/leonardt/fault/blob/master/fault/verilator_target.py

It provides concrete implementations for the `make_<action>` methods and `run`
method which generate a C++ file used as the verilator test harness.  The
generation of the test harness is done using string templating of C++ code.

### SystemVerilogTarget
The source code for the `SystemVerilog` can be found in
https://github.com/leonardt/fault/blob/master/fault/system_verilog_target.py

Similarly to the `VerilatorTarget` it provides concrete implementations of the
`make_<action>` and `run` methods using string templating to generate system
verilog code.

One key `__init__` parameter is `simulator` which selects between `ncsim` and
`vcs`. This parameter mainly affects the `run` method, which dispatches on the
value to determine the correct CLI to use for invoking the simulator. 

### CoSA
The source code for the `CoSATarget` can be found in
https://github.com/leonardt/fault/blob/master/fault/cosa_target.py

It has only been tested with the `SymbolicTester` with at least one assumption
and guarantee.  

Non assume or guarantee actions are used to generate an `ets` file (e.g. for
generating a sequences of pokes to set up the state of the circuit).

Assumptions are compiled to the `assume:` field of the CoSA problem file
format, and guarantees are compiled to the `formula: ` field.

Notice that the compilation of assumptions and formulas rely on rewriting the
Python lambda expressions into the format expected by CoSA (e.g.
https://github.com/leonardt/fault/blob/master/fault/cosa_target.py#L142). The
current mechanism for rewriting is not robust nor complete and should be
improved by developing a clear specification for the property language and a
generic rewriter of the Python AST into an AST that can be serialized into the
syntax expected by CoSA.

## Roadmap
### Simulation Actions
#### Loops
In the current state, loops in fault test benches are executed in Python.  That
is, they are part of the metaprogram stage. This is useful for metaprogramming
with loops, but inefficient for test benches that contain large loops that do
not need to be unrolled at the metaprogramming stage.  To address this issue,
`fault` should provide a loop action which accepts a function from loop index
to a sequnce of actions.  This allows the user to stage the body of a loop,
without executing it in Python.  This action should be code generated by the
target into the approriate looping construct for the target language.

#### File IO
File IO is a useful pattern for constructing test benches (e.g. streaming input
and output images from and to files).  Fault should provide actions for
opening, reading from, and closing files. This, combined with a looping action,
will enable users to stage test logic based on file contents without having to
actually open the file and loop over it during the metaprogramming phase. This
has the benefit of keeping the test harness simpler (by not having to "unroll
the file") as well as enabling the generated harness to be resueable across
multiple input/output files.

#### Monitors
A common pattern in hardware testing is the concept of a `Monitor` which is an
entity which *monitors* the circuit and enforces certain guarantees.  For
example, a monitor might check an input enable signal and then assert that an
output is present after a specified number of cycles.  This requires compiling
the monitor specification into the target language, and therefor requires the
specification of the langauge and a strategy for rewriting the AST into the
target language AST for serialization.  There is likely overlap between this
feature and the property specification langauge discussed in the roadmap for
the formal section.

### Constrained Random
Input stimuli based on assumptions are generated by filtering valid values out
of a stream of random numbers (see
https://github.com/leonardt/fault/blob/master/fault/verilator_target.py#L327-L337).
This is all done in Python and is very inefficient for complex constraints.
This area of the system could be improved by moving to a more sophisticated
constraint solver and by providing user hooks to specify the random
distribution to sample from.  The logic to generate input stimuli could
also be moved to the target languages, which would allow the test benches to
be reused with different input stimuli without having to recompile them.

### Formal
The main issue with the `assume`/`guarantee` interface, as discussed in the
above section on the CoSA target, is the translation of the specification
language to the target language expected by CoSA. To improve the state of this,
the specification language should be precisely defined, and the translation
should be done using a generic AST rewriter and serializer.  This specification
language should also include facilities for describing temporal properties
(currently we only support "combinational" properties).

Another extension would be the integration of simluation and formal. That is,
simulation actions (e.g. `poke`, `step`) can be run using a standard simulator
to setup the state of the circuit under test. Then, this state can be dumped
and provided to the CoSA tool as the state.  In some cases, this approach will
be less expensive than having the solver setup the state using a mechanism like
the `ets` which requires unrolling in time.
