import magma as m
import fault
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'verilog-ams')


def test_vams_sim(target, simulator, vsup=1.5):
    # declare the circuit
    dut = m.DeclareCircuit(
        'mysram',
        'wl', m.In(m.Bit),
        'lbl', m.InOut(m.Bit),
        'lblb', m.InOut(m.Bit),
        'vdd', m.In(m.Bit),
        'vss', m.In(m.Bit)
    )

    # instantiate the tester
    tester = fault.SRAMTester(dut)

    # Run the simulation
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/mysram.sp').resolve()],
        use_spice=['mysram'],
        vsup=vsup,
        ext_model_file=True,
        tmp_dir=True
    )
