import fault
import mantle
import magma as m


def pytest_generate_tests(metafunc):
    fault.pytest_sim_params(metafunc, 'system-verilog')


def test_env_mod(target, simulator):
    myinv = m.DefineCircuit('myinv', 'a', m.In(m.Bit), 'y', m.Out(m.Bit))
    m.wire(~myinv.a, myinv.y)
    m.EndDefine()

    tester = fault.InvTester(myinv, in_='a', out='y')

    tester.compile_and_run(target=target, simulator=simulator, tmp_dir=True)
