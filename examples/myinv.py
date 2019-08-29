import magma as m
import fault
from pathlib import Path

# declare circuit
dut = m.DeclareCircuit('myinv', 'in_', m.BitIn, 'out', m.BitOut,
                       'vdd', m.BitIn, 'vss', m.BitIn)

# define the test
t = fault.Tester(dut)
t.poke(dut.vss, False)
t.poke(dut.vdd, True)
t.poke(dut.in_, False)
t.expect(dut.out, True)
t.poke(dut.in_, True)
t.expect(dut.out, False)

# run the test
t.compile_and_run(target='spice', simulator='ngspice', vsup=1.5,
                  model_paths=[Path('myinv.sp').resolve()])
