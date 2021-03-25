import tempfile
import fault as f
from ..common import SimpleALU, pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


def test_user_namespace(target, simulator):
    t = f.SynchronousTester(SimpleALU, SimpleALU.CLK)
    t.circuit.config_en = 1
    t.circuit.config_data = 0
    t.advance_cycle()
    t.circuit.a = 1
    t.circuit.b = 2
    t.advance_cycle()
    t.circuit.c.expect(3)
    with tempfile.TemporaryDirectory(dir=".") as _dir:
        if target == "verilator":
            t.compile_and_run(target, directory=_dir, flags=["-Wno-fatal"],
                              magma_opts={"user_namespace": "my_namespace",
                                          "sv": True})
        else:
            t.compile_and_run(target, directory=_dir, simulator=simulator,
                              magma_opts={"user_namespace": "my_namespace",
                                          "sv": True})
