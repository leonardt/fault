import fault
import magma as m
import mantle


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_env_mod(target, simulator):
    myinv = m.DefineCircuit('myinv', 'a', m.In(m.Bit), 'y', m.Out(m.Bit))
    m.wire(~myinv.a, myinv.y)
    m.EndDefine()

    tester = fault.Tester(myinv)

    tester.poke(myinv.a, 1)
    tester.expect(myinv.y, 0)
    tester.poke(myinv.a, 0)
    tester.expect(myinv.y, 1)

    tester.compile_and_run(target=target, simulator=simulator, tmp_dir=True)
