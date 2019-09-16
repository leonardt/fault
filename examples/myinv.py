import fault

# declare circuit
dut = fault.DeclareFromSpice('myinv.sp')

# define the test
t = fault.Tester(dut, expect_strict_default=True)
t.poke(dut.vss, 0)
t.poke(dut.vdd, 1)
t.poke(dut.in_, 0)
t.expect(dut.out, 1)
t.poke(dut.in_, 1)
t.expect(dut.out, 0)

# run the test
t.compile_and_run(target='spice', vsup=1.5)
