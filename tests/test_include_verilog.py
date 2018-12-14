import pathlib
import tempfile
import fault
import magma as m
import os


def pytest_generate_tests(metafunc):
    if "target" in metafunc.fixturenames:
        targets = [("verilator", None)]
        if not os.getenv("TRAVIS", False):
            targets.append(("system-verilog", "ncsim"))
            targets.append(("system-verilog", "vcs"))
        metafunc.parametrize("target,simulator", targets)


def test_include_verilog(target, simulator):
    SB_DFF = m.DeclareCircuit('SB_DFF', "D", m.In(m.Bit), "Q", m.Out(m.Bit),
                              "C", m.In(m.Clock))
    main = m.DefineCircuit('main', "I", m.In(m.Bit), "O", m.Out(m.Bit),
                           *m.ClockInterface())
    ff = SB_DFF()
    m.wire(ff.D, main.I)
    m.wire(ff.Q, main.O)
    m.EndDefine()

    tester = fault.Tester(main, main.CLK)
    tester.poke(main.CLK, 0)
    tester.poke(main.I, 1)
    tester.eval()
    tester.expect(main.O, 0)
    tester.step(2)
    tester.expect(main.O, 1)
    sb_dff_filename = pathlib.Path("tests/sb_dff_sim.v").resolve()

    kwargs = {}
    if simulator is not None:
        kwargs["simulator"] = simulator

    with tempfile.TemporaryDirectory() as tmp_dir:
        tester.compile_and_run(target=target, directory=tmp_dir,
                               include_verilog_libraries=[sb_dff_filename], **kwargs)

    if target in ["verilator"]:
        # Should work by including the tests/ directory which contains the verilog
        # file SB_DFF.v
        dir_path = os.path.dirname(os.path.realpath(__file__))
        with tempfile.TemporaryDirectory() as tmp_dir:
            tester.compile_and_run(target=target, directory=tmp_dir,
                                   include_directories=[dir_path], **kwargs)
