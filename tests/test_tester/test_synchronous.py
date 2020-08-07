from fault import SynchronousTester
from hwtypes import BitVector
from ..common import SimpleALU, pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


def test_synchronous_basic(target, simulator):
    ops = [
        lambda x, y: x + y,
        lambda x, y: x - y,
        lambda x, y: x * y,
        lambda x, y: y - x
    ]
    tester = SynchronousTester(SimpleALU, SimpleALU.CLK)
    for i in range(4):
        tester.circuit.a = a = BitVector.random(16)
        tester.circuit.b = b = BitVector.random(16)
        tester.circuit.config_data = i
        tester.circuit.config_en = 1
        tester.advance_cycle()
        # Make sure enable low works
        tester.circuit.config_data = BitVector.random(2)
        tester.circuit.config_en = 0
        tester.circuit.c.expect(ops[i](a, b))
        tester.advance_cycle()

    if target == "verilator":
        tester.compile_and_run("verilator", flags=['-Wno-unused'])
    else:
        tester.compile_and_run(target, simulator=simulator,
                               magma_opts={"sv": True})
