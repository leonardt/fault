import pytest
from pysv import sv, DataType
from pysv.util import clear_imports
import fault
import magma as m
from hwtypes import BitVector
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, "system-verilog", "verilator",
                      exclude=["vivado", "iverilog"])


class dut(m.Circuit):
    io = m.IO(A=m.In(m.Bits[4]), B=m.In(m.Bits[4]), O=m.Out(m.Bits[4]))
    io += m.ClockIO()
    io.CLK.unused()
    io.O @= io.A + io.B


def run_tester(tester, target, simulator):
    kwargs = {
        "target": target,
        # "disp_type": "realtime",
        "simulator": simulator,
        "magma_opts": {"sv": True},
        "tmp_dir": False
    }

    if target == "verilator":
        kwargs.pop("simulator")
        # notice that since verilator commands are generated when the tester
        # is initialized, we can't keep track of inserted imported functions
        # in the constructor. as a result user need to specify the flag in
        # the constructor
        kwargs["use_pysv"] = True
        # force verilator to use C++11. This is only needed if the compiler is
        # ancient, e.g. gcc-4.8
        kwargs["flags"] = ["--CFLAGS", "-std=c++11"]

    # run the test
    tester.compile_and_run(**kwargs)


def test_function(target, simulator):
    @sv(a=DataType.UByte, b=DataType.UByte, return_type=DataType.UByte)
    def gold_func(a, b):
        return a + b

    clear_imports(gold_func)
    tester = fault.Tester(dut)
    tester.poke(tester.circuit.A, 1)
    tester.poke(tester.circuit.B, 1)
    tester.eval()
    tester.expect(tester.circuit.O,
                  tester.make_call_expr(gold_func, tester.circuit.A,
                                        tester.circuit.B))
    # test out assigning values
    v = tester.Var("v", BitVector[4])
    tester.poke(v, tester.make_call_expr(gold_func, tester.circuit.A,
                                         tester.circuit.B))
    tester.eval()
    tester.expect(tester.circuit.O, v)

    run_tester(tester, target, simulator)


def test_class(target, simulator):
    class Model:
        @sv(b=DataType.UByte)
        def __init__(self, b):
            self.b = b

        @sv(a=DataType.UByte)
        def add(self, a):
            return a + self.b

        @sv()
        def incr(self, amount):
            self.b += amount

    clear_imports(Model)
    a_value = 1
    tester = fault.Tester(dut)
    tester.poke(tester.circuit.A, a_value)
    tester.poke(tester.circuit.B, 1)

    model = tester.Var("model", Model)
    tester.poke(model, tester.make_call_expr(Model, a_value))

    # start testing. using a loop
    loop = tester.loop(10)
    loop.poke(tester.circuit.B, loop.index)
    loop.eval()
    loop.expect(tester.circuit.O, tester.make_call_expr(model.add, loop.index))

    tester.make_call_stmt(model.incr, BitVector[32](2))

    tester.expect(tester.circuit.O, tester.make_call_expr(model.add, 9) - 2)

    run_tester(tester, target, simulator)


def test_monitor(target, simulator):
    class DelayedDUT(m.Circuit):
        io = m.IO(A=m.In(m.Bits[4]), B=m.In(m.Bits[4]), O=m.Out(m.Bits[4]))
        io += m.ClockIO(has_enable=True)
        io.O @= m.Register(m.Bits[4], has_enable=True)()(dut()(io.A, io.B),
                                                         CE=io.CE)

    # TODO: Using a subclass breaks pysv
    # class Monitor(fault.PysvMonitor):
    class Monitor:
        @sv()
        def __init__(self):
            self.value = None

        @sv()
        def observe(self, A, B, O):
            print(A, B, self.value)
            if self.value is not None:
                assert O == self.value, f"{O} != {self.value}"
            # TODO: Referencing bitvector here doesn't work, so just manually
            # mask for now
            # self.value = BitVector[4](A) + BitVector[4](B)
            self.value = (A + B) & ((1 << 4) - 1)
            print(f"next value {self.value}")

    clear_imports(Monitor)

    def test(circuit, enable):
        tester = fault.SynchronousTester(circuit)
        monitor = tester.Var("monitor", Monitor)
        tester.poke(monitor, tester.make_call_expr(Monitor))
        tester.attach_monitor(monitor)
        tester.poke(circuit.CE, enable)

        for i in range(4):
            tester.poke(tester.circuit.A, BitVector.random(4))
            tester.poke(tester.circuit.B, BitVector.random(4))
            tester.advance_cycle()
        tester.advance_cycle()

        run_tester(tester, target, simulator)
    # Should work
    test(DelayedDUT, 1)
    with pytest.raises(AssertionError):
        # Should fail
        test(DelayedDUT, 0)


if __name__ == "__main__":
    test_class("verilator", None)
