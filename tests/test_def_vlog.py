import fault
import magma as m
from pathlib import Path


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_def_vlog(target, simulator, n_bits=8, b_val=42):
    defadd = m.DeclareCircuit('defadd', 'a_val', m.In(m.Bits[n_bits]),
                              'c_val', m.Out(m.Bits[n_bits]))

    tester = fault.Tester(defadd)

    tester.poke(defadd.a_val, 12)
    tester.expect(defadd.c_val, 54)

    tester.poke(defadd.a_val, 34)
    tester.expect(defadd.c_val, 76)

    tester.compile_and_run(
        target=target,
        simulator=simulator,
        ext_libs=[Path('tests/verilog/defadd.sv').resolve()],
        ext_model_file=True,
        defines={'N_BITS': n_bits, 'B_VAL': b_val},
        tmp_dir=True,
        skip_compile=True
    )
