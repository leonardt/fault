from pathlib import Path
import fault
import magma as m


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_ext_vlog(target, simulator):
    myinv = m.DeclareCircuit('myinv', 'in_', m.In(m.Bit), 'out', m.Out(m.Bit))

    tester = fault.Tester(myinv)

    tester.poke(myinv.in_, 1)
    tester.expect(myinv.out, 0)

    tester.poke(myinv.in_, 0)
    tester.expect(myinv.out, 1)

    # run the test
    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/myinv.v').resolve()],
        ext_model_file=True,
        tmp_dir=True,
        skip_compile=True
    )
