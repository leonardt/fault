from pathlib import Path
import magma as m
import fault
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', 'verilog-ams', 'spice')


def test_inv(target, simulator):
    circuit_name = 'myinv'
    ports = dict(in_=m.BitIn, out=m.BitOut)
    run_generic(circuit_name=circuit_name, ports=ports,
                tester_cls=fault.InvTester, target=target,
                simulator=simulator)


def test_nand(target, simulator):
    circuit_name = 'mynand'
    ports = dict(a=m.BitIn, b=m.BitIn, out=m.BitOut)
    run_generic(circuit_name=circuit_name, ports=ports,
                tester_cls=fault.NandTester, target=target,
                simulator=simulator)


def test_sram(target, simulator):
    circuit_name = 'mysram'
    ports = dict(wl=m.BitIn, lbl=m.BitInOut, lblb=m.BitInOut)
    run_generic(circuit_name=circuit_name, ports=ports,
                tester_cls=fault.SRAMTester, target=target,
                simulator=simulator)


def run_generic(circuit_name, ports, tester_cls, target, simulator, vsup=1.5):
    # add supply pins if needed
    if target in ['verilog-ams', 'spice']:
        ports = ports.copy()
        ports['vdd'] = m.BitIn
        ports['vss'] = m.BitIn

    # declare circuit
    class dut(m.Circuit):
        name = circuit_name
        io = m.IO(**ports)

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
        kwargs['model_paths'] = [Path(f'tests/spice/{circuit_name}.sp').resolve()]  # noqa
        kwargs['vsup'] = vsup
    if target == 'verilog-ams':
        kwargs['use_spice'] = [circuit_name]
    if target == 'system-verilog':
        kwargs['ext_libs'] = [Path(f'tests/verilog/{circuit_name}.v').resolve()]  # noqa

    # compile and run
    tester.compile_and_run(**kwargs)
