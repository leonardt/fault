import magma as m
import fault
from pathlib import Path

# declare circuit
dut = m.DeclareCircuit('myinv', 'in_', m.BitIn, 'out', m.BitOut,
                       'vdd', m.BitIn, 'vss', m.BitIn)

# define the test
t = fault.Tester(dut)
t.poke(dut.vss, 0)
t.poke(dut.vdd, 1)
t.poke(dut.in_, 0)
t.expect(dut.out, 1)
t.poke(dut.in_, 1)
t.expect(dut.out, 0)

# run the test
t.compile_and_run(target='spice', simulator='ngspice', vsup=1.5,
                  model_paths=[Path('myinv.sp').resolve()])