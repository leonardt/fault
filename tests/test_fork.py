from pathlib import Path
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_fork_join(target, simulator):
    class dut(m.Circuit):
        # add dummy clock
        io = m.IO(I=m.In(m.Bits[4]), O=m.Out(m.Bits[4]), clk=m.In(m.Clock))
        io.O @= io.I

    tester = fault.Tester(dut)
    proc1 = tester.fork("proc1")
    proc2 = tester.fork("proc2")

    for i, proc in enumerate([proc1, proc2]):
        proc.poke(tester.circuit.I[1 - i], 1)
        proc.eval()
        proc.wait_until_high(tester.circuit.I[i])
        proc.poke(tester.circuit.I[i + 2], 1)

    tester.join(proc1, proc2)
    tester.eval()
    tester.expect(tester.circuit.O, 0xF)

    tester.compile_and_run(
        target=target,
        simulator=simulator,
        tmp_dir=False
    )
