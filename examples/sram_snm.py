import magma as m
import fault
from pathlib import Path


# define circuit name
CIRCUIT_NAME = 'sram_snm'

# define path to circuit
THIS_DIR = Path(__file__).resolve().parent
CIRCUIT_PATH = THIS_DIR / f'{CIRCUIT_NAME}.sp'

# define simulator name (ngspice, spectre, or hspice)
SIMULATOR = 'ngspice'

# define the supply voltage
VDD = 1.5

# define the amount to time to wait before checking
# the bit value
TD = 100e-9

# define the number of iterations to run
N_ITER = 15


def run(noise=0.0):
    # declare circuit
    dut = m.DeclareCircuit(
        CIRCUIT_NAME,
        'lbl', m.BitInOut,
        'lblb', m.BitInOut,
        'vdd', m.BitIn,
        'vss', m.BitIn,
        'wl', m.BitIn
    )

    # instantiate the tester
    tester = fault.Tester(dut, poke_delay_default=0)

    # initialize
    tester.poke(dut.lbl, fault.HiZ)
    tester.poke(dut.lblb, fault.HiZ)
    tester.poke(dut.vdd, True)
    tester.poke(dut.vss, False)
    tester.poke(dut.wl, True)
    tester.delay(TD)

    # read back data, expecting "0"
    tester.expect(dut.lbl, False)
    tester.expect(dut.lblb, True)

    # specify initial conditions

    ic = {tester.internal('lbl_x'): noise,
          tester.internal('lblb_x'): VDD - noise,
          dut.lbl: VDD,
          dut.lblb: VDD}

    # run the test
    tester.compile_and_run(
        ic=ic,
        vsup=VDD,
        target='spice',
        simulator=SIMULATOR,
        model_paths=[CIRCUIT_PATH]
    )


def main():
    dn, up = 0, VDD
    for k in range(N_ITER):
        noise = 0.5 * (up + dn)
        print(f'Iteration {k}: noise={noise}')
        try:
            run(noise=noise)
        except (fault.A2DError, AssertionError):
            up = noise
        else:
            dn = noise
    print(f'Noise: {0.5*(up+dn)}')


if __name__ == '__main__':
    main()
