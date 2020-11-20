from pysv import sv
import fault
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog', exclude=["vivado", "iverilog"])


def test_function(target, simulator):
    class dut(m.Circuit):
        # add dummy clock
        io = m.IO(A=m.In(m.Bits[4]), B=m.In(m.Bits[4]), O=m.Out(m.Bits[4]))
        io.O @= io.A + io.B

    tester = fault.Tester(dut)

    @sv()
    def gold_func(a, b):
        return a + b

    tester.poke(tester.circuit.A, 1)
    tester.poke(tester.circuit.B, 1)
    tester.eval()
    tester.expect(tester.circuit.O,
                  tester.make_call(gold_func,
                                   tester.circuit.A, tester.circuit.B))

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        tmp_dir=False
    )
