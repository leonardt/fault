# Fault
![Linux Test](https://github.com/leonardt/fault/workflows/Linux%20Test/badge.svg)
![MacOS Test](https://github.com/leonardt/fault/workflows/MacOS%20Test/badge.svg)
[![BuildKite Status](https://badge.buildkite.com/c724929c65201c6ed5aebc027ffac02b5092d0bd8fad4341b6.svg?branch=master)](https://buildkite.com/stanford-aha/fault)
[![Code Coverage](https://codecov.io/gh/leonardt/fault/branch/master/graph/badge.svg)](https://codecov.io/gh/leonardt/fault)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A Python package for testing hardware (part of the magma ecosystem).

[API Documentation](http://truong.io/fault/)

[CHANGELOG](./CHANGELOG.md)

## Installation
```
pip install fault
```

## Documentation
Check out the [fault tutorial](https://github.com/leonardt/fault/tree/master/tutorial)

* [Actions](https://github.com/leonardt/fault/blob/master/doc/actions.md)
* [Tester](https://github.com/leonardt/fault/blob/master/doc/tester.md)
* [Integrating External Verilog](https://github.com/leonardt/fault/blob/master/doc/verilog_integration.ipynb)
* [Properties](https://github.com/leonardt/fault/blob/master/doc/property.md)

## Supported Simulators

* Digital simulation
  * [Verilator](https://www.veripool.org/wiki/verilator)
  * [Icarus Verilog](http://iverilog.icarus.com)
  * [Cadence Incisive/Xcelium](https://www.cadence.com/en_US/home/tools/system-design-and-verification/simulation-and-testbench-verification/xcelium-parallel-simulator.html)
  * [Synopsys VCS](https://www.synopsys.com/verification/simulation/vcs.html)
  * [Xilinx Vivado](https://www.xilinx.com/products/design-tools/vivado.html)
* Formal verification
  * Engines supported by [pySMT](https://github.com/pysmt/pysmt)
* Analog simulation
  * [ngspice](http://ngspice.sourceforge.net)
  * [Cadence Spectre](https://www.cadence.com/en_US/home/tools/custom-ic-analog-rf-design/circuit-simulation/spectre-simulation-platform.html)
  * [Synopsys HSPICE](https://www.synopsys.com/verification/ams-verification/hspice.html)
* Mixed-signal simulation
  * [Verilog-AMS](https://www.verilogams.com) via Cadence Incisive/Xcelium

## Example
Here is a simple ALU defined in magma.
```python
import magma as m
import mantle


class ConfigReg(m.Circuit):
    io = m.IO(D=m.In(m.Bits[2]), Q=m.Out(m.Bits[2])) + \
        m.ClockIO(has_ce=True)

    reg = mantle.Register(2, has_ce=True, name="conf_reg")
    io.Q @= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    io = m.IO(
        a=m.In(m.UInt[16]),
        b=m.In(m.UInt[16]),
        c=m.Out(m.UInt[16]),
        config_data=m.In(m.Bits[2]),
        config_en=m.In(m.Enable)
    ) + m.ClockIO()

    opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
    io.c @= mantle.mux(
        [io.a + io.b, io.a - io.b, io.a * io.b, io.a ^ io.b], opcode)
```

Here's an example test in fault that uses the configuration interface, expects
a value on the internal register, and checks the result of performing the
expected operation.

```python
import operator
import fault

ops = [operator.add, operator.sub, operator.mul, operator.floordiv]
tester = fault.Tester(SimpleALU, SimpleALU.CLK)
tester.circuit.CLK = 0
tester.circuit.config_en = 1
for i in range(0, 4):
    tester.circuit.config_data = i
    tester.step(2)
    tester.circuit.a = 3
    tester.circuit.b = 2
    tester.eval()
    tester.circuit.c.expect(ops[i](3, 2))
```

We can run this with three different simulators

```python
tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")
tester.compile_and_run("system-verilog", simulator="ncsim", directory="build")
tester.compile_and_run("system-verilog", simulator="vcs", directory="build")
```

### Working with internal signals
Fault supports peeking, expecting, and printing internal signals. For the
`verilator` target, you should use the keyword argument `magma_opts` with
`"verilator_debug"` set to true.  This will cause coreir to compile the verilog
with the required debug comments.  Example:
```python
tester.compile_and_run("verilator", flags=["-Wno-fatal"], 
                       magma_opts={"verilator_debug": True}, directory="build")
```

If you're using `mantle.Register` from the `coreir` implementation, you can
also poke the internal register value directly using the `value` field.  Notice
that `conf_reg` is defined in `ConfigReg` to be an instance of
`mantle.Register` and the test bench pokes it by setting `confg_reg.value`
equal to `1`.

```python
tester = fault.Tester(SimpleALU, SimpleALU.CLK)
tester.circuit.CLK = 0
# Set config_en to 0 so stepping the clock doesn't clobber the poked value
tester.circuit.config_en = 0
# Initialize
tester.step(2)
for i in reversed(range(4)):
    tester.circuit.config_reg.conf_reg.value = i
    tester.step(2)
    tester.circuit.config_reg.conf_reg.O.expect(i)
    # You can also print these internal signals using the getattr interface
    tester.print("O=%d\n", tester.circuit.config_reg.conf_reg.O)
```

## FAQ

### How can I write test bench logic that depends on the runtime state of the circuit?
A common pattern in testing is to only perform certain actions depending on the
state of the circuit.  For example, one may only want to expect an output value
when a valid signal is high, ignoring it otherwise.  Another pattern is to change
the expected value over time by using a looping structure.  Finally, one may
want to expect a value that is a function of other runtime values.  To support
these pattern, `fault` provides support "peeking" values, performing expressions
on "peeked" values, if statements, and while loops.  

#### Peek Expressions
Suppose we had a circuit as follows:
```python
class BinaryOpCircuit(m.Circuit):
    io = m.IO(I0=m.In(m.UInt[5]), I1=m.In(m.UInt[5]), O=m.Out(m.UInt[5]))

    io.O @= io.I0 + io.I1 & (io.I1 - io.I0)
```
We can write a generic test that expects the output `O` in terms
of the inputs `I0` and `I1` (rather than computing the expected value in
Python).
```python
tester = fault.Tester(BinaryOpCircuit)
for _ in range(5):
    tester.poke(tester._circuit.I0, hwtypes.BitVector.random(5))
    tester.poke(tester._circuit.I1, hwtypes.BitVector.random(5))
    tester.eval()
    expected = tester.circuit.I0 + tester.circuit.I1
    expected &= tester.circuit.I1 - tester.circuit.I0
    tester.circuit.O.expect(expected)
```
This is a useful pattern for writing reuseable test components (e.g.  composign
the output checking logic with various input stimuli generators).

#### Control Structures
The `tester._while(<test>)` action accepts a Peek value or expression as the test condition for a loop and returns a child tester that allows the user to add actions to the body of the loop.  Here's a simple example that loops until a done signal is asserted, printing some debug information in the loop body:
```python
# Wait for loop to complete
loop = tester._while(dut.n_done)
debug_print(loop, dut)
loop.step()
loop.step()

# check final state
tester.circuit.count.expect(expected_num_cycles - 1)
```
Notice that you can also add actions after the loop to check expected behavior
after the loop has completed.

The `tester._if(<test>)` action behaves similarly by accepting a test peek value or expression and conditionally executes actions depending on the
result of the expression.  Here is a simple example:
```python
if_tester = tester._if(tester.circuit.O == 0)
if_tester.circuit.I = 1
else_tester = if_tester._else()
else_tester.circuit.I = 0
tester.eval()
```

The `tester._for(<num_iter>)` action provides a simple way to write a loop over
a fixed number of iterations.  Use the attribute `index` to get access to the
current iteration, for example:
```python
loop = tester._for(8)
loop.poke(circ.I, loop.index)
loop.eval()
tester.expect(circ.O, loop.index)
```

### What Python values can I use to poke/expect ports?
Here are the supported Python values for poking the following port types:
* `m.Bit` - `bool` (`True`/`False`) or `int` (`0`/`1`) or `hwtypes.Bit`
* `m.Bits[N]` - `hwtypes.BitVector[N]`, `int` (where the number of bits used to
  express it is equal to `N`)
* `m.SInt[N]` - `hwtypes.SIntVector[N]`, `int` (where the number of bits used to
  express it is equal to `N`)
* `m.UInt[N]` - `hwtypes.UIntVector[N]`, `int` (where the number of bits used to
  express it is equal to `N`)
* `m.Array[N, T]` - `list` (where the length of the list is equal to `N` and
  the elements recursively conform to the supported types of values for `T`).
  For example, suppose I have a port `I` of type `m.Array[3, m.Bits[3]]`. 
  I can poke it as follows:
  ```python
  val = [random.randint(0, (1 << 4) - 1) for _ in range(3)]
  tester.poke(circ.I, val)
  ```
  You can also poke it by element as follows:
  ```python
  for i in range(3):
      val = random.randint(0, (1 << 4) - 1)
      tester.poke(circ.I[i], val)
      tester.eval()
      tester.expect(circ.O[i], val)
  ```
* `m.Tuple(a=m.Bits[4], b=m.Bits[4])` - `tuple` (where the length of the tuple is equal to the number of fields), `dict` (where there is a one-to-one mapping between key/value pairs to the tuple fields).  Example:
  ```python
  tester.circuit.I = (4, 2)
  tester.eval()
  tester.circuit.O.expect((4, 2))
  tester.circuit.I = {"a": 4, "b": 2}
  tester.eval()
  tester.circuit.O.expect({"a": 4, "b": 2})
  ```

### How do I generate waveforms with fault?

Fault supports generating `.vcd` dumps when using the `verilator` and
`system-verilog/ncsim` target.

For the `verilator` target, use the `flags` keyword argument to pass the
`--trace` flag.  For example,

    tester.compile_and_run("verilator", flags=["-Wno-fatal", "--trace"])

The `--trace` flag must be passed through to verilator so it generates code
that supports waveform dumping. The test harness generated by fault will
include the required logic for invoking `tracer->dump(main_time)` for every
call to `eval` and `step`.  `main_time` is incremented for every call to step.
The output `.vcd` file will be saved in the file `logs/{circuit_name}` where
`circuit_name` is the name of the ciruit passed to `Tester`.  The `logs`
directory will be placed in the same directory as the generated harness, which
is controlled by the `directory` keyword argument (by default this is
`"build/"`).

For the `system-verilog` target, enable this feature using the
`compile_and_run` parameter `dump_waveform=True`.  By default, the waveform
file will be named `waveforms.vcd` for `ncsim` and `waveforms.vpd` for `vcs`.
The name of the file can be changed using the parameter
`waveform_file="<file_name>"`.  

The `vcs` simulator also supports dumping `fsdb` by using the argument
`waveform_type="fsdb"`.  For this to work, you'll need to also use the `flags`
argument using the path defined in your verdi manual.  For example,
`$VERDI_HOME/doc/linking_dumping.pdf`.  

Here is an example using an older version of verdi (using the VERDIHOME
environment variable):
```python
verdi_home = os.environ["VERDIHOME"]
# You may need to change the 'vcs_latest' and 'LINUX64' parts of the path
# depending on your verdi version, please consult
# $VERDI_HOME/doc/linking_dumping.pdf
flags = ['-P', 
         f' {verdi_home}/share/PLI/vcs_latest/LINUX64/novas.tab',
         f' {verdi_home}/share/PLI/vcs_latest/LINUX64/pli.a']
tester.compile_and_run(target="system-verilog", simulator="vcs",
                       waveform_type="fsdb", dump_waveforms=True, flags=flags)
```

Here's an example for a newer version of verdi
```python
verdi_home = os.environ["VERDI_HOME"]
flags = ['-P',
         f' {verdi_home}/share/PLI/VCS/linux64/novas.tab',
         f' {verdi_home}/share/PLI/VCS/linux64/pli.a']
tester.compile_and_run(target="system-verilog", simulator="vcs",
                       waveform_type="fsdb", dump_waveforms=True, flags=flags)
```

To configure fsdb dumping, use the `fsdb_dumpvars_args` parameter of the
compile_and_run command to pass a string to the `$fsdbDumpvars()` function.

For example:
```python
tester.compile_and_run(target="system-verilog", simulator="vcs",
                       waveform_type="fsdb", dump_waveforms=True,
                       fsdb_dumpvars_args='0, "dut"')
```

will produce:
```verilog
  $fsdbDumpvars(0, "dut");
```

inside the generated test bench.

### How do I pass through flags to the simulator?
The `verilator` and `system-verilog` target support the parameter `flags` which
accepts a list of flags (strings) that will be passed through to the simulator
command (`verilator` for verilator, `irun` for ncsim, `vcs` for vcs, and
`iverilog` for iverilog).

### Can I include a message to print when an expect fails?
Use the `msg` argument to the expect action. You can either pass a standalone
string, e.g.
```python
tester.circuit.O.expect(0, msg="my error message")
```

or you can pass a printf/$display style message using a tuple.  The first argument
should be the format string, the subsequent arguments are the format values,
e.g.
```python
tester.circuit.O.expect(0, msg=("MY_MESSAGE: got %x, expected 0!",
                                tester.circuit.O))
```

### Can I display or print values from my testbench?
Yes, you can use the `tester.print` API which accepts a format string and a
variable number of arguments.  Here's an example:
```python
tester = fault.Tester(circ, circ.CLK)
tester.poke(circ.I, 0)
tester.eval()
tester.expect(circ.O, 0)
tester.poke(circ.CLK, 0)
tester.step()
tester.print("%08x\n", circ.O)
```


### Can I just generate a test bench without running it?
Yes, here's an example:
```python
# compile the tester
tester.compile("verilator")
# generate the test bench file (returns the name of the file)
tb_file = tester.generate_test_bench("verilator")
```

or for system verilog
```python
tester.compile("system-verilog", simulator="ncsim")
tb_file = tester.generate_test_bench("system-verilog")
```
