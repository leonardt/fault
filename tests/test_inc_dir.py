import fault
import magma as m
from pathlib import Path
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'system-verilog')


def test_inc_dir(target, simulator):
    # declare circuit
    class mybuf_inc_test(m.Circuit):
        io = m.IO(
            in_=m.In(m.Bit),
            out=m.Out(m.Bit)
        )

    # define the test
    tester = fault.BufTester(mybuf_inc_test)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/mybuf_inc_test.v').resolve()],
        inc_dirs=[Path('tests/verilog').resolve()],
        ext_model_file=True,
        tmp_dir=True
    )
