import pathlib
import tempfile
import fault
import magma as m
import os
import shutil


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if shutil.which("irun"):
            targets.append(("system-verilog", "ncsim"))
        if shutil.which("vcs"):
            targets.append(("system-verilog", "vcs"))
        metafunc.parametrize("target,simulator", targets)


def test_include_verilog(target, simulator):
    # define flip-flop (external implementation)
    class SB_DFF(m.Circuit):
        io = m.IO(
            D=m.In(m.Bit),
            Q=m.Out(m.Bit),
            C=m.In(m.Clock)
        )

    # define main circuit that instantiates external flip-flop
    class main(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit)) + m.ClockIO()
        ff = SB_DFF()
        ff.D @= io.I
        io.O @= ff.Q

    # define the test
    tester = fault.Tester(main, main.CLK)
    tester.poke(main.CLK, 0)
    tester.poke(main.I, 1)
    tester.eval()
    tester.expect(main.O, 0)
    tester.step(2)
    tester.expect(main.O, 1)

    # define location of flip-flop implementation
    sb_dff_filename = pathlib.Path("tests/sb_dff_sim.v").resolve()

    kwargs = {}
    if simulator is not None:
        kwargs["simulator"] = simulator

    with tempfile.TemporaryDirectory(dir=".") as tmp_dir:
        tester.compile_and_run(target=target, directory=tmp_dir,
                               include_verilog_libraries=[sb_dff_filename],
                               **kwargs)

    if target in ["verilator"]:
        # Should work by including the tests/ directory which contains the
        # verilog file SB_DFF.v
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with tempfile.TemporaryDirectory(dir=".") as tmp_dir:
            tester.compile_and_run(target=target, directory=tmp_dir,
                                   include_directories=[dir_path], **kwargs)
