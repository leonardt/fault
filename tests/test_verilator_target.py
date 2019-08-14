import tempfile
import magma as m
import fault
from hwtypes import BitVector
from fault.actions import Poke, Expect, Eval, Step, Print, Peek
from fault.tester import Tester
import os.path
from .common import TestBasicCircuit, TestBasicClkCircuit


def test_verilator_peeks():
    circ = TestBasicCircuit
    actions = [
        Poke(circ.I, 1),
        Expect(circ.O, Peek(circ.O))
    ]
    flags = ["-Wno-lint"]
    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        m.compile(f"{tempdir}/{circ.name}", circ, output="coreir-verilog")
        target = fault.verilator_target.VerilatorTarget(
            circ, directory=f"{tempdir}/",
            flags=flags, skip_compile=True)
        target.run(actions)


def test_verilator_skip_build():
    circ = TestBasicCircuit
    flags = ["-Wno-lint"]
    tester = Tester(circ)
    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        tester.compile_and_run(target="verilator",
                               directory=tempdir,
                               flags=flags)
        # get the timestamp on generated verilator obj files
        obj_filename = os.path.join(tempdir, "obj_dir", "VBasicCircuit__ALL.a")
        mtime = os.path.getmtime(obj_filename)

        # run without building the verilator
        tester.compile_and_run(target="verilator",
                               directory=tempdir,
                               skip_verilator=True,
                               flags=flags)
        new_mtime = os.path.getmtime(obj_filename)
        assert mtime == new_mtime


def test_verilator_trace():
    circ = TestBasicClkCircuit
    actions = [
        Poke(circ.I, 0),
        Print("%x", circ.I),
        Expect(circ.O, 0),
        Poke(circ.CLK, 0),
        Print("%x", circ.O),
        Step(circ.CLK, 1),
        Poke(circ.I, BitVector[1](1)),
        Eval(),
        Print("%x", circ.O),
    ]
    flags = ["-Wno-lint", "--trace"]

    with tempfile.TemporaryDirectory(dir=".") as tempdir:
        assert not os.path.isfile(f"{tempdir}/logs/BasicClkCircuit.vcd"), \
            "Expected logs to be empty"
        m.compile(f"{tempdir}/{circ.name}", circ,
                  output="coreir-verilog")
        target = fault.verilator_target.VerilatorTarget(
            circ, directory=f"{tempdir}/",
            flags=flags, skip_compile=True)
        target.run(actions)
        assert os.path.isfile(f"{tempdir}/logs/BasicClkCircuit.vcd"), \
            "Expected VCD to exist"
