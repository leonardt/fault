import magma as m
import fault
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'verilog-ams')


def test_inv_tf(
    target, simulator, n_steps=100, vsup=1.5, vil_rel=0.4, vih_rel=0.6,
    vol_rel=0.1, voh_rel=0.9
):

    # declare circuit and wrap
    myinv = m.DeclareCircuit(
        'myinv',
        'in_', fault.RealIn,
        'out', fault.RealOut,
        'vdd', fault.RealIn,
        'vss', fault.RealIn
    )
    dut = fault.VAMSWrap(myinv)

    # define the test
    tester = fault.Tester(dut)
    tester.poke(dut.vdd, vsup)
    tester.poke(dut.vss, 0)
    for k in range(n_steps):
        in_ = k * vsup / (n_steps - 1)
        tester.poke(dut.in_, in_)
        if in_ <= vil_rel * vsup:
            tester.expect(dut.out, vsup, above=voh_rel * vsup)
        elif in_ >= vih_rel * vsup:
            tester.expect(dut.out, 0, below=vol_rel * vsup)

    # run the simulation
    myinv_fname = Path('tests/spice/myinv.sp').resolve()
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        model_paths=[myinv_fname],
        use_spice=['myinv'],
        vsup=vsup,
        tmp_dir=True
    )
