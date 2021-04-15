from fault import Tester
from .common import TestBasicCircuit
import tempfile
import os
import pytest
import shutil


def test_verilator_coverage():
    circ = TestBasicCircuit
    tester = Tester(circ)
    # dummy input and outputs to provide
    # input for the coverage
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 1)

    with tempfile.TemporaryDirectory() as temp:
        tester.compile_and_run(
            target="verilator",
            coverage=True,
            directory=temp
        )

        print(os.listdir(os.path.join(temp, "logs")))
        # make sure it generates a non empty file
        cov_file = os.path.join(temp, "logs", "coverage.dat")
        assert os.path.isfile(cov_file)
        assert os.stat(cov_file).st_size > 0


def test_ncsim_coverage():
    irun = shutil.which("irun")
    if irun is None:
        pytest.skip("ncsim not found")
    circ = TestBasicCircuit
    tester = Tester(circ)
    # dummy input and outputs to provide
    # input for the coverage
    tester.zero_inputs()
    tester.poke(circ.I, 1)
    tester.eval()
    tester.expect(circ.O, 1)

    with tempfile.TemporaryDirectory() as temp:
        tester.compile_and_run(
            target="system-verilog",
            simulator="ncsim",
            coverage=True,
            directory=temp
        )

        # make sure it generates a non empty file
        cov_dir = os.path.join(temp, "cov_work")
        assert os.path.isdir(cov_dir)
        assert len(os.listdir(cov_dir)) > 0


if __name__ == "__main__":
    test_ncsim_coverage()
