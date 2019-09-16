from pathlib import Path

import magma as m

import fault
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_ext_vlog(target, simulator):
    tester = fault.Tester(m.DeclareCircuit('mytb'))

    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_srcs=[Path('tests/verilog/mytb.sv').resolve()],
        ext_test_bench=True,
        tmp_dir=True
    )
