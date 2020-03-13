import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_ext_tb(target, simulator):
    class mytb(m.Circuit):
        io = m.IO()

    tester = fault.Tester(mytb)
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_srcs=[Path('tests/verilog/mytb.sv').resolve()],
        ext_test_bench=True,
        tmp_dir=True
    )
