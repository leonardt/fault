import magma as m
import fault
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'spice')


def test_spice_bus(target, simulator, vsup=1.5):
    # declare circuit
    dut = m.DeclareCircuit(
        'mybus',
        'a', m.In(m.Bits[2]),
        'b', m.Out(m.Bits[3]),
        'vdd', m.BitIn,
        'vss', m.BitIn
    )

    # define the test
    tester = fault.Tester(dut)
    tester.poke(dut.vdd, 1)
    tester.poke(dut.vss, 0)

    # step through all possible inputs
    tester.poke(dut.a, 0b000)
    tester.expect(dut.b, 0b101)
    tester.poke(dut.a, 0b001)
    tester.expect(dut.b, 0b100)
    tester.poke(dut.a, 0b010)
    tester.expect(dut.b, 0b111)
    tester.poke(dut.a, 0b011)
    tester.expect(dut.b, 0b110)

    # test one bit of the bus at a time
    tester.poke(dut.a[0], 0)
    tester.expect(dut.b[0], 1)
    tester.poke(dut.a[0], 1)
    tester.expect(dut.b[0], 0)
    tester.expect(dut.b[2], 1)

    tester.poke(dut.a[1], 0)
    tester.expect(dut.b[1], 0)
    tester.poke(dut.a[1], 1)
    tester.expect(dut.b[1], 1)
    tester.expect(dut.b[2], 1)

    # set options
    kwargs = dict(
        target=target,
        simulator=simulator,
        model_paths=[Path('tests/spice/mybus.sp').resolve()],
        vsup=vsup,
        tmp_dir=True
    )

    # run the simulation
    tester.compile_and_run(**kwargs)
