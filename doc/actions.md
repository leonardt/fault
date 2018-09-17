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
