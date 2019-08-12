import magma as m
import fault
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog', 'verilog-ams')


def test_sram(target, simulator, vsup=1.5):
    # declare the circuit
    ports = []
    ports += ['wl', m.In(m.Bit)]
    ports += ['lbl', m.InOut(m.Bit)]
    ports += ['lblb', m.InOut(m.Bit)]
    if target == 'verilog-ams':
        ports += ['vdd', m.In(m.Bit)]
        ports += ['vss', m.In(m.Bit)]
    dut = m.DeclareCircuit('mysram', *ports)

    # instantiate the tester
    tester = fault.SRAMTester(dut)

    # Run the simulation
    kwargs = dict(
        target=target,
        simulator=simulator,
        ext_model_file=True,
        tmp_dir=True
    )
    if target == 'verilog-ams':
        kwargs['model_paths'] = [Path('tests/spice/mysram.sp').resolve()]
        kwargs['use_spice'] = ['mysram']
        kwargs['vsup'] = vsup
    elif target == 'system-verilog':
        kwargs['ext_libs'] = [Path('tests/verilog/mysram.v').resolve()]

    # compile and run
    tester.compile_and_run(**kwargs)
