import pytest
from fault import SynchronousTester
import magma as m
from hwtypes import BitVector
from ..common import SimpleALU, pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, 'verilator', 'system-verilog')


def test_synchronous_basic(target, simulator):
    ops = [
        lambda x, y: x + y,
        lambda x, y: x - y,
        lambda x, y: x * y,
        lambda x, y: y - x
    ]
    tester = SynchronousTester(SimpleALU, SimpleALU.CLK)
    for i in range(4):
        tester.circuit.a = a = BitVector.random(16)
        tester.circuit.b = b = BitVector.random(16)
        tester.circuit.config_data = i
        tester.circuit.config_en = 1
        tester.advance_cycle()
        # Make sure enable low works
        tester.circuit.config_data = BitVector.random(2)
        tester.circuit.config_en = 0
        tester.circuit.c.expect(ops[i](a, b))
        tester.advance_cycle()

    if target == "verilator":
        tester.compile_and_run("verilator")
    else:
        tester.compile_and_run(target, simulator=simulator,
                               magma_opts={"sv": True})


def test_find_default_clock():
    tester = SynchronousTester(SimpleALU)
    assert tester.clock == SimpleALU.CLK


def test_find_default_clock_nested():
    class Foo(m.Circuit):
        io = m.IO(
            I=m.In(m.Tuple[m.Clock, m.Bit])
        )
    tester = SynchronousTester(Foo)
    assert tester.clock == Foo.I[0]


def test_find_default_clock_multiple():
    class Foo(m.Circuit):
        io = m.IO(
            clock0=m.In(m.Clock),
            clock1=m.In(m.Clock)
        )
    with pytest.raises(ValueError) as e:
        SynchronousTester(Foo)
    assert str(e.value) == "SynchronousTester requires a clock"


def test_find_default_clock_nested_multiple():
    class Foo(m.Circuit):
        io = m.IO(
            I=m.In(m.Tuple[m.Clock, m.Clock])
        )
    with pytest.raises(ValueError) as e:
        SynchronousTester(Foo)
    assert str(e.value) == "SynchronousTester requires a clock"
