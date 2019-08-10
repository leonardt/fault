import magma as m
import fault
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'verilog-ams')


def test_vams_sim(target, simulator, n_trials=100, vsup=1.5):
    # define the circuit
    dut = m.DeclareCircuit(
        'myinv',
        'in_', m.In(m.Bit),
        'out', m.Out(m.Bit),
        'vdd', m.In(m.Bit),
        'vss', m.In(m.Bit)
    )

    # define the test
    tester = fault.Tester(dut)
    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)
    for _ in range(n_trials):
        # generate random bit
        in_ = fault.random_bit()
        # send stimulus and check output
        tester.poke(dut.in_, in_)
        tester.eval()
        tester.expect(dut.out, not in_, strict=True)

    # Run the simulation
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/myinv.sp').resolve()],
        use_spice=['myinv'],
        vsup=vsup,
        ext_model_file=True,
        tmp_dir=True
    )
