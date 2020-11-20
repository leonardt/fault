from pysv import sv, DataType
import fault
import magma as m
from hwtypes import BitVector
from .common import pytest_sim_params


def pytest_generate_tests(metafunc):
    pytest_sim_params(metafunc, "system-verilog", "verilator", exclude=["vivado", "iverilog"])


class dut(m.Circuit):
    io = m.IO(A=m.In(m.Bits[4]), B=m.In(m.Bits[4]), O=m.Out(m.Bits[4]))
    io.O @= io.A + io.B


def run_tester(tester, target, simulator):
    kwargs = {
        "target": target,
        "simulator": simulator,
        "tmp_dir": False
    }

    if target == "verilator":
        kwargs.pop("simulator")
        # notice that since verilator commands are generated when the tester is initialized
        # we can't keep track of inserted imported functions in the constructor. as a result
        # user need to specify the flag in the constructor
        kwargs["use_pysv"] = True

    # run the test
    tester.compile_and_run(**kwargs)


def test_function(target, simulator):
    @sv(a=DataType.UByte, b=DataType.UByte, return_type=DataType.UByte)
    def gold_func(a, b):
        return a + b

    tester = fault.Tester(dut)
    tester.poke(tester.circuit.A, 1)
    tester.poke(tester.circuit.B, 1)
    tester.eval()
    tester.expect(tester.circuit.O,
                  tester.make_call(gold_func,
                                   tester.circuit.A, tester.circuit.B))
    # test out assigning values
    v = tester.Var("v", BitVector[4])
    tester.poke(v, tester.make_call(gold_func, tester.circuit.A, tester.circuit.B))
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

    a_value = 1
    tester = fault.Tester(dut)
    tester.poke(tester.circuit.A, a_value)
    tester.poke(tester.circuit.B, 1)

    model = tester.Var("model", Model)
    tester.poke(model, tester.make_call(Model, a_value))

    # start testing
    tester.poke(tester.circuit.B, 1)
    tester.eval()
    tester.expect(tester.circuit.O, tester.make_call(Model.add, 1))

    run_tester(tester, target, simulator)


if __name__ == "__main__":
    test_class("verilator", None)
