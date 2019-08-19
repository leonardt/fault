import magma as m
import fault
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent


def run(target='spice', simulator='ngspice', vsup=1.5, noise=0.0, td=5e-9):
    # declare circuit
    sram = m.DeclareCircuit(
        'sram_snm',
        'lbl', m.BitInOut,
        'lblb', m.BitInOut,
        'noise', fault.RealIn,
        'vdd', m.BitIn,
        'vss', m.BitIn,
        'wl', m.BitIn
    )

    # wrap if needed
    if target == 'verilog-ams':
        dut = fault.VAMSWrap(sram)
    else:
        dut = sram

    # instantiate the tester
    tester = fault.Tester(dut)

    # initialize
    tester.poke(dut.lbl, 0, delay=td)
    tester.poke(dut.lblb, 0, delay=td)
    tester.poke(dut.noise, 0, delay=td)
    tester.poke(dut.vdd, 1, delay=td)
    tester.poke(dut.vss, 0, delay=td)
    tester.poke(dut.wl, 0, delay=td)

    # write a "0"
    tester.poke(dut.lbl, 0, delay=td)
    tester.poke(dut.lblb, 1, delay=td)
    tester.poke(dut.wl, 1, delay=td)
    tester.poke(dut.wl, 0, delay=td)

    # apply noise
    tester.poke(dut.noise, noise, delay=td)
    tester.poke(dut.noise, 0, delay=td)

    # precharge
    tester.poke(dut.lbl, 1, delay=td)
    tester.poke(dut.lblb, 1, delay=td)

    # set to Hi-Z
    tester.poke(dut.lbl, fault.HiZ, delay=td)
    tester.poke(dut.lblb, fault.HiZ, delay=td)

    # access bit
    tester.poke(dut.wl, 1, delay=td)

    # read back data, expecting "0"
    tester.expect(dut.lbl, 0, strict=True)
    tester.expect(dut.lblb, 1, strict=True)

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[THIS_DIR / 'sram_snm.sp'],
        vsup=vsup,
        t_tr=td / 10,
        tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['use_spice'] = ['sram_snm']

    # run the simulation
    tester.compile_and_run(**kwargs)


def main(vsup=1.5):
    dn, up = 0, vsup
    for k in range(15):
        noise = 0.5 * (up + dn)
        print(f'Iteration {k}: noise={noise}')
        try:
            run(vsup=vsup, noise=noise)
        except (fault.A2DError, AssertionError):
            up = noise
        else:
            dn = noise
    print(f'Noise: {0.5*(up+dn)}')


if __name__ == '__main__':
    main()
