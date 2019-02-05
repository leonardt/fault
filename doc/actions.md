# Actions
The action pattern is the fundamental abstraction of fault testers. Using actions, clients of tester can construct sequences of inputs to circuits as well as assertions on the outputs of those circuits. The tester/action abstraction mirrors event-driven simulation semantics.

We provide an interface to the following actions

## Poke
`Poke(port, value)` stages stimulating port `port` to be `value`. `port` must be an input. Note that pokes are not propagated to combinational outputs; see [Eval](#eval) semantics.

## Expect
`Expect(port, value)` issues an assertion that port `port` reads value `value`. `port` must be an output. The values read by output ports at the time of Expect are the same as those at the time of the last Eval.

## Eval
`Eval()` propagates all inputs staged by [Poke](#poke) to combinational outputs. Synchronous outputs do not change (unless the clock has been explicitly toggled with Poke).

## Step
`Step(clock_port, num_steps)` toggles the clock (specified by `clock_port`) for `num_steps` half-periods, evaluating the outputs before each clock edge.

One instance of `Step(clock_port, n)` is equivalent to the following sequence:

```python
# Assume starts at 0, without loss of generality.
clk_val = 0

for i in range(n):
    Eval()
    clk_val = ~clk_val
    Poke(clock_port, clk_val)
```

## Print
`Print(port, format_str)` prints the value read at `port` (`port` can be an input or an output). Similar to Expect, the values read by output ports at the time of Print are the same as those at the time of the last Eval.

`format_str` allows for user-specified formatting of the printed output (similar to `printf` format strings).

## WrappedVerilogInternalPort
Fault has primitive support for working with internal verilog signals using the
`verilator` target.

Suppose you had a file `simple_alu.v`. Notice that the desired internal
signals, `ConfigReg.Q` and `SimpleALU.opcode` are marked with a comment
`/*verilator public*/`.

```verilog
// simple_alu.v
module ConfigReg(input [1:0] D, output [1:0] Q, input CLK, input EN);
reg Q/*verilator public*/;
always @(posedge CLK) begin
    if (EN) Q <= D;
end
endmodule

module SimpleALU(input [15:0] a, input [15:0] b, output [15:0] c, input [1:0] config_data, input config_en, input CLK);

wire [1:0] opcode/*verilator public*/;
ConfigReg config_reg(config_data, opcode, CLK, config_en);


always @(*) begin
    case (opcode)
        0: c = a + b;
        1: c = a - b;
        2: c = a * b;
        3: c = a / b;
    endcase
end
endmodule
```

We can wrap the verilog using magma

```python
SimpleALU = m.DefineFromVerilogFile("tests/simple_alu.v",
                                    type_map={"CLK": m.In(m.Clock)},
                                    target_modules=["SimpleALU"])[0]

circ = m.DefineCircuit("top",
                       "a", m.In(m.Bits(16)),
                       "b", m.In(m.Bits(16)),
                       "c", m.Out(m.Bits(16)),
                       "config_data", m.In(m.Bits(2)),
                       "config_en", m.In(m.Bit),
                       "CLK", m.In(m.Clock))
simple_alu = SimpleALU()
m.wire(simple_alu.a, circ.a)
m.wire(simple_alu.b, circ.b)
m.wire(simple_alu.c, circ.c)
m.wire(simple_alu.config_data, circ.config_data)
m.wire(simple_alu.config_en, circ.config_en)
m.wire(simple_alu.CLK, circ.CLK)
m.EndDefine()
```

Here's an example test we can write using the internal signals

```python
    tester = fault.Tester(circ, circ.CLK)
    tester.verilator_include("SimpleALU")
    tester.verilator_include("ConfigReg")
    tester.poke(circ.config_en, 1)
    for i in range(0, 4):
        tester.poke(circ.config_data, i)
        tester.step(2)
        tester.expect(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.opcode",
                                             m.Bits(2)),
            i)
        signal = tester.peek(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.opcode",
                                             m.Bits(2)))
        tester.expect(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.opcode",
                                             m.Bits(2)),
            signal)
        tester.expect(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.config_reg.Q",
                                             m.Bits(2)),
            i)
        signal = tester.peek(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.config_reg.Q",
                                             m.Bits(2)))
        tester.expect(
            fault.WrappedVerilogInternalPort("top.SimpleALU_inst0.config_reg.Q",
                                             m.Bits(2)),
            signal)
```

Notice that the test must include the desired wrapped module with the statement
`tester.verilator_include("simple_alu")`. This is so the generated C harness
includes the verilator generated header.  To expect or peek a port, you can use
`WrappedVerilogInternalPort` and provide the verilator C++ style path through
the instance hierarchy to the desired port.
