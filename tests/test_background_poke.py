import fault
from .common import pytest_sim_params, TestBasicCircuit


def pytest_generate_tests(metafunc):
    # Not implemented for verilator because this doesn't make much sense
    # without a concept of delay
    pytest_sim_params(metafunc, 'system-verilog')


def test_clock_verilog(target, simulator):
    circ = TestBasicCircuit
    tester = fault.Tester(circ)
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 1)

    # register clock
    tester.poke(circ.I, 0, delay={'freq': 1e9, 'duty_cycle': 0.75})

    # This delay would move the "expect"s off the edge.
    # Right now, the test ensures that an expect directly on the edge gets the
    # post-edge value.
    # tester.delay(.0625e-9)

    # Break the cycle into eighths. First 2 eighths read 0, next 6 read 1
    for i in range(100):
        for j in range(2):
            tester.eval()
            tester.expect(circ.O, 0)
            tester.delay(0.125e-9)
        for j in range(6):
            tester.eval()
            tester.expect(circ.O, 1)
            tester.delay(0.125e-9)

    tester.print("%08x", circ.O)

    if target == "verilator":
        tester.compile_and_run(target, tmp_dir=True, flags=["-Wno-fatal"])
    else:
        tester.compile_and_run(target, tmp_dir=True, simulator=simulator)
