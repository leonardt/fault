import fault
import magma as m
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_ext_vlog(target, simulator):
    tester = fault.Tester(m.DeclareCircuit('mytb'))

    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_srcs=[Path('tests/verilog/mytb.sv').resolve()],
        ext_test_bench=True,
        tmp_dir=True
    )
