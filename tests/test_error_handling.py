import fault
import pytest
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


@pytest.mark.xfail(strict=True)
def test_error_task(target, simulator):
    class error_task(m.Circuit):
        io = m.IO()

    tester = fault.Tester(error_task)
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_srcs=[Path('tests/verilog/error_task.sv').resolve()],
        ext_test_bench=True,
        tmp_dir=True
    )


@pytest.mark.xfail(strict=True)
def test_fatal_task(target, simulator):
    class fatal_task(m.Circuit):
        io = m.IO()

    tester = fault.Tester(fatal_task)
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_srcs=[Path('tests/verilog/fatal_task.sv').resolve()],
        ext_test_bench=True,
        tmp_dir=True
    )
