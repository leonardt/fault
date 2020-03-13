import fault
import mantle
import magma as m
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_env_mod(target, simulator):
    class myinv(m.Circuit):
        io = m.IO(
            a=m.In(m.Bit),
            y=m.Out(m.Bit)
        )
        io.y @= ~io.a

    tester = fault.InvTester(myinv, in_='a', out='y')
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        tmp_dir=True
    )
