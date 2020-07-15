import shutil

import pytest
import fault as f
import magma as m


def test_basic_assert():
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8])) + m.ClockIO()
        io.O @= m.Register(T=m.Bits[8])()(io.I)
        f.assert_(io.I | f.implies | f.delay[1] | io.O, on=f.posedge(io.CLK))
        f.assert_(f.sva(io.I, "|-> ##1", io.O), on=f.posedge(io.CLK))

    if not shutil.which("ncsim"):
        return pytest.skip("need ncsim for SVA test")
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.O.expect(1)
    tester.circuit.I = 0
    tester.advance_cycle()
    tester.circuit.O.expect(0)
    tester.advance_cycle()
    tester.circuit.I = 1
    tester.circuit.O.expect(0)
    tester.advance_cycle()
    tester.circuit.I = 0
    tester.circuit.O.expect(1)
    tester.advance_cycle()
    tester.circuit.O.expect(0)
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})


@pytest.mark.parametrize("sva", [True, False])
def test_basic_assert_fail(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8])) + m.ClockIO()
        io.O @= m.Register(T=m.Bits[8])()(io.I)
        if sva:
            f.assert_(f.sva(io.I, "|-> ##1", io.O.value() == 0),
                      on=f.posedge(io.CLK))
        else:
            f.assert_(io.I | f.implies | f.delay[1] | (io.O.value() == 0),
                      on=f.posedge(io.CLK))

    if not shutil.which("ncsim"):
        return pytest.skip("need ncsim for SVA test")

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 0
    tester.advance_cycle()
    tester.advance_cycle()
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.advance_cycle()
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@pytest.mark.parametrize("sva", [True, False])
def test_variable_delay(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        if sva:
            f.assert_(f.sva(io.write, "|-> ##[1:2]", io.read),
                      on=f.posedge(io.CLK))
            f.assert_(f.sva(io.write, "|-> ##[*]", io.read),
                      on=f.posedge(io.CLK))
            f.assert_(f.sva(io.write, "|-> ##[+]", io.read),
                      on=f.posedge(io.CLK))
        else:
            f.assert_(io.write | f.implies | f.delay[1:2] | io.read,
                      on=f.posedge(io.CLK))
            f.assert_(io.write | f.implies | f.delay[0:] | io.read,
                      on=f.posedge(io.CLK))
            f.assert_(io.write | f.implies | f.delay[1:] | io.read,
                      on=f.posedge(io.CLK))

    if not shutil.which("ncsim"):
        return pytest.skip("need ncsim for SVA test")

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 1
    tester.advance_cycle()
    tester.circuit.write = 0
    tester.circuit.read = 1
    tester.advance_cycle()
    tester.circuit.write = 1
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.circuit.write = 0
    tester.advance_cycle()
    tester.circuit.read = 1
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 1
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.advance_cycle()
    tester.advance_cycle()
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 1
    tester.circuit.read = 1
    tester.advance_cycle()
    # Does not pass 1 or more cycles
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.advance_cycle()
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@pytest.mark.parametrize("sva", [True, False])
def test_repetition(sva, capsys):
    # TODO: Parens/precedence with nested sequences (could wrap in seq object?)
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        N = 2
        if sva:
            seq0 = f.sva(~io.read, "##1", io.write)
            seq1 = f.sva(io.read, "##1", io.write)
            f.assert_(f.sva(seq0, "|-> ##1", io.read, f"[*{N}] ##1", seq1),
                      on=f.posedge(io.CLK))
        else:
            seq0 = ~io.read | f.delay[1] | io.write
            seq1 = io.read | f.delay[1] | io.write
            f.assert_(seq0 | f.implies | f.delay[1] | io.read | f.repeat[N] |
                      f.delay[1] | seq1, on=f.posedge(io.CLK))

    if not shutil.which("ncsim"):
        return pytest.skip("need ncsim for SVA test")

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 0
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.circuit.write = 1
    tester.advance_cycle()
    for _ in range(2):
        tester.circuit.write = 0
        tester.circuit.read = 1
        tester.advance_cycle()
    # Should fail if we don't see seq2
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out
    tester.circuit.write = 0
    tester.circuit.read = 1
    tester.advance_cycle()
    tester.circuit.write = 1
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.circuit.write = 0
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})


@pytest.mark.parametrize("sva", [True, False])
@pytest.mark.parametrize("zero_or_one", [0, 1])
def test_repetition_or_more(sva, zero_or_one, capsys):
    # TODO: Parens/precedence with nested sequences (could wrap in seq object?)
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        if sva:
            seq0 = f.sva(~io.read, "##1", io.write)
            seq1 = f.sva(io.read, "##1", io.write)
            symb = "*" if zero_or_one == 0 else "+"
            f.assert_(f.sva(seq0, "|-> ##1", io.read, f"[{symb}] ##1", seq1),
                      on=f.posedge(io.CLK))
        else:
            seq0 = ~io.read | f.delay[1] | io.write
            seq1 = io.read | f.delay[1] | io.write
            f.assert_(seq0 | f.implies | f.delay[1] | io.read |
                      f.repeat[zero_or_one:] | f.delay[1] | seq1,
                      on=f.posedge(io.CLK))

    if not shutil.which("ncsim"):
        return pytest.skip("need ncsim for SVA test")

    for i in range(0, 3):
        tester = f.SynchronousTester(Main, Main.CLK)
        tester.circuit.write = 0
        tester.circuit.read = 0
        tester.advance_cycle()
        tester.circuit.write = 1
        tester.advance_cycle()
        # Should fail if we don't see seq2
        with pytest.raises(AssertionError):
            tester.compile_and_run("system-verilog", simulator="ncsim",
                                   flags=["-sv"], magma_opts={"inline": True})
        # do repeated sequence i times
        for _ in range(i):
            tester.circuit.write = 0
            tester.circuit.read = 1
            tester.advance_cycle()
        tester.circuit.write = 0
        tester.circuit.read = 1
        tester.advance_cycle()
        tester.circuit.write = 1
        tester.circuit.read = 0
        tester.advance_cycle()
        tester.circuit.write = 0
        tester.advance_cycle()
        if i == 0 and zero_or_one == 1:
            # Should fail on first try (0 times)
            with pytest.raises(AssertionError):
                tester.compile_and_run("system-verilog", simulator="ncsim",
                                       flags=["-sv"],
                                       magma_opts={"inline": True})
        else:
            tester.compile_and_run("system-verilog", simulator="ncsim",
                                   flags=["-sv"], magma_opts={"inline": True})
