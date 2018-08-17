import magma as m
import mantle
from fault.test_vectors import generate_function_test_vectors, \
    generate_simulator_test_vectors
from common import TestBasicCircuit, TestArrayCircuit, TestSIntCircuit
import pytest

import shutil
import os


def setup_function():
    os.mkdir("tests/build")


def teardown_function():
    shutil.rmtree("tests/build")


@pytest.mark.parametrize("Circuit", [TestBasicCircuit, TestArrayCircuit,
                                     TestSIntCircuit])
def test_circuit(Circuit):
    def fn(I):
        return I
    function_test_vectors = generate_function_test_vectors(Circuit, fn)
    simulator_test_vectors = generate_simulator_test_vectors(Circuit)
    assert function_test_vectors == simulator_test_vectors


def test_basic_circuit():
    def f(a, b, c):
        return (a & b) ^ c

    class main(m.Circuit):
        IO = ["a", m.In(m.Bit), "b", m.In(m.Bit), "c", m.In(m.Bit),
              "d", m.Out(m.Bit)]

        @classmethod
        def definition(io):
            m.wire(f(io.a, io.b, io.c), io.d)
    m.compile("tests/build/main", main, "coreir-verilog")

    from fault.verilator_target import VerilatorTarget

    test_vectors = generate_function_test_vectors(main, f)

    VerilatorTarget(main, test_vectors, "tests/build").run()
