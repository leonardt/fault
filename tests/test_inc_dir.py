import fault
import magma as m
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_ext_vlog(target, simulator):
    # declare circuit
    mybuf = m.DeclareCircuit(
        'mybuf',
        'in_', m.In(m.Bit),
        'out', m.Out(m.Bit)
    )

    # define the test
    tester = fault.Tester(mybuf)
    tester.poke(mybuf.in_, 1)
    tester.expect(mybuf.out, 1)
    tester.poke(mybuf.in_, 0)
    tester.expect(mybuf.out, 0)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/mybuf.v').resolve()],
        inc_dirs=[Path('tests/verilog').resolve()],
        ext_model_file=True,
        tmp_dir=True
    )
