import magma as m
import mantle
import operator
import fault
import pytest
from hwtypes import BitVector
import os


class ConfigReg(m.Circuit):
    io = m.IO(D=m.In(m.Bits[2]), Q=m.Out(m.Bits[2])) + \
        m.ClockIO(has_ce=True)

    reg = mantle.Register(2, has_ce=True, name="conf_reg")
    io.Q @= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              c=m.Out(m.UInt[16]),
              config_data=m.In(m.Bits[2]),
              config_en=m.In(m.Enable),
              ) + m.ClockIO()

    opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
    io.c @= mantle.mux(
        [io.a + io.b, io.a - io.b, io.a * io.b, io.a ^ io.b], opcode)


def test_simple_alu():
    ops = [operator.add, operator.sub, operator.mul, operator.xor]
    tester = fault.Tester(SimpleALU, SimpleALU.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    for i in range(0, 4):
        tester.circuit.config_data = i
        tester.step(2)
        tester.circuit.a = 3
        tester.circuit.b = 2
        tester.eval()
        tester.circuit.c.expect(ops[i](3, 2))

    tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")


@pytest.mark.parametrize("opcode, op",
                         enumerate(["add", "sub", "mul", "floordiv"]))
def test_simple_alu_parametrized(opcode, op):
    op = getattr(operator, op)
    tester = fault.Tester(SimpleALU, SimpleALU.CLK)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    tester.circuit.config_data = opcode
    tester.step(4)
    tester.circuit.a = 3
    tester.circuit.b = 2
    tester.eval()
    tester.circuit.c.expect(op(BitVector[16](3), BitVector[16](2)))

    os.system("rm -r build/*")
    tester.compile_and_run("verilator", flags=["-Wno-fatal"], directory="build")


@pytest.mark.parametrize("target,strategy", [("verilator", "rejection"),
                                             ("verilator", "smt"),
                                             ("cosa", None)])
def test_simple_alu_assume_guarantee(target, strategy):
    tester = fault.SymbolicTester(SimpleALU, SimpleALU.CLK, num_tests=100,
                                  random_strategy=strategy)
    tester.circuit.CLK = 0
    tester.circuit.config_en = 1
    tester.circuit.config_data = 0
    tester.step(2)
    tester.circuit.config_en = 0
    tester.step(2)
    if target == "verilator":
        # NOTE: Currently the cosa backend does not support the expect action
        tester.circuit.config_reg.Q.expect(0)
    tester.circuit.a.assume(lambda a: a < BitVector[16](32768))
    tester.circuit.b.assume(lambda b: b < BitVector[16](32768))
    # tester.circuit.b.assume(lambda b: b >= BitVector[16](32768))

    tester.circuit.c.guarantee(lambda a, b, c: (c >= a) and (c >= b))
    kwargs = {}
    if target == "verilator":
        kwargs["flags"] = ["-Wno-fatal"]
        kwargs["magma_opts"] = {"verilator_debug": True}
    elif target == "cosa":
        kwargs["magma_opts"] = {"passes": ["rungenerators", "flatten",
                                           "cullgraph"]}
    os.system("rm -r build/*")
    tester.compile_and_run(target, directory="build", **kwargs)
