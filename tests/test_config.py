import fault
import os
import fault.config
from .common import TestTupleCircuit


def test_config_test_dir():
    file_dir = os.path.dirname(__file__)
    harness_file = os.path.join(file_dir, "build/TupleCircuit_driver.cpp")
    # Remove harness if it exists to ensure that it's recreated properly
    if os.path.isfile(harness_file):
        os.remove(harness_file)
    fault.config.set_test_dir('callee_file_dir')
    circ = TestTupleCircuit
    tester = fault.Tester(circ)
    tester.circuit.I.a = 5
    tester.circuit.I.b = 11
    tester.eval()
    tester.circuit.O.a.expect(5)
    tester.circuit.O.b.expect(11)
    tester.compile_and_run("verilator", directory="build",
                           flags=['-Wno-fatal'])
    fault.config.set_test_dir('normal')
    assert os.path.isfile(harness_file), \
        "Verilator harness not created relative to current file"
