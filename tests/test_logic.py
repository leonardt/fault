from pathlib import Path
import magma as m
import fault


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog', 'verilog-ams', 'spice')


def test_inv(target, simulator):
    name = 'myinv'
    ports = ['in_', m.BitIn, 'out', m.BitOut]
    run_generic(name=name, ports=ports, tester_cls=fault.InvTester,
                target=target, simulator=simulator)


def test_nand(target, simulator):
    name = 'mynand'
    ports = ['a', m.BitIn, 'b', m.BitIn, 'out', m.BitOut]
    run_generic(name=name, ports=ports, tester_cls=fault.NandTester,
                target=target, simulator=simulator)


def test_sram(target, simulator):
    name = 'mysram'
    ports = ['wl', m.BitIn, 'lbl', m.BitInOut, 'lblb', m.BitInOut]
    run_generic(name=name, ports=ports, tester_cls=fault.SRAMTester,
                target=target, simulator=simulator)


def run_generic(name, ports, tester_cls, target, simulator, vsup=1.5):
    # declare the circuit, adding supply pins if needed
    if target in ['verilog-ams', 'spice']:
        ports = ports.copy()
        ports += ['vdd', m.BitIn]
        ports += ['vss', m.BitIn]
    dut = m.DeclareCircuit(name, *ports)

    # define the test content
    tester = tester_cls(dut)

    # define run options
    kwargs = dict(
        target=target,
        simulator=simulator,
        tmp_dir=True
    )
    if target in ['verilog-ams', 'system-verilog']:
        kwargs['ext_model_file'] = True
    if target in ['verilog-ams', 'spice']:
        kwargs['model_paths'] = [Path(f'tests/spice/{name}.sp').resolve()]
        kwargs['vsup'] = vsup
    if target == 'verilog-ams':
        kwargs['use_spice'] = [name]
    if target == 'system-verilog':
        kwargs['ext_libs'] = [Path(f'tests/verilog/{name}.v').resolve()]

    # compile and run
    tester.compile_and_run(**kwargs)
