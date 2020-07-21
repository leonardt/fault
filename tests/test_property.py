import shutil
import random

import pytest
import decorator
import fault as f
import magma as m


def requires_ncsim(test_fn):
    def wrapper(test_fn, *args, **kwargs):
        if not shutil.which("ncsim"):
            return pytest.skip("need ncsim for SVA test")
        return test_fn(*args, **kwargs)
    return decorator.decorator(wrapper, test_fn)


@requires_ncsim
def test_basic_assert():
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8])) + m.ClockIO()
        io.O @= m.Register(T=m.Bits[8])()(io.I)
        f.assert_(io.I | f.implies | f.delay[1] | io.O, on=f.posedge(io.CLK))
        f.assert_(f.sva(io.I, "|-> ##1", io.O), on=f.posedge(io.CLK))
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


@requires_ncsim
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


@requires_ncsim
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


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_repetition(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        N = 2
        if sva:
            seq0 = f.sequence(f.sva(~io.read, "##1", io.write))
            seq1 = f.sequence(f.sva(io.read, "##1", io.write))
            f.assert_(f.sva(~io.read & ~io.write, "[*2] |->", seq0,
                            f"[*{N}] ##1", seq1), on=f.posedge(io.CLK))
        else:
            seq0 = f.sequence(~io.read | f.delay[1] | io.write)
            seq1 = f.sequence(io.read | f.delay[1] | io.write)
            f.assert_(~io.read & ~io.write | f.repeat[2] | f.implies | seq0 |
                      f.repeat[N] | f.delay[1] | seq1, on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 0
    tester.circuit.read = 0
    tester.advance_cycle()
    for _ in range(2):
        tester.circuit.write = 0
        tester.circuit.read = 0
        tester.advance_cycle()
        tester.circuit.write = 1
        tester.advance_cycle()
    # Should fail if we don't see seq2
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out, out
    tester.circuit.write = 0
    tester.circuit.read = 1
    tester.advance_cycle()
    tester.circuit.write = 1
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.circuit.write = 0
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})


@requires_ncsim
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
        out, _ = capsys.readouterr()
        assert "Assertion Main_tb.dut.__assert_1 has failed" in out
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


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
@pytest.mark.parametrize("num_reps", [3, slice(3, 5)])
def test_goto_repetition(sva, num_reps, capsys):
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        if sva:
            symb = num_reps
            if isinstance(symb, slice):
                symb = f"{symb.start}:{symb.stop}"
            f.assert_(f.sva(io.write == 1, f"[-> {symb}]", '##1', io.read,
                            '##1', io.write), on=f.posedge(io.CLK))
        else:
            f.assert_((io.write == 1) | f.goto[num_reps] | f.delay[1] | io.read
                      | f.delay[1] | io.write, on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 1
    tester.circuit.read = 0
    n = num_reps
    if isinstance(n, slice):
        n = random.randint(n.start, n.stop)
    for i in range(n):
        tester.advance_cycle()
    tester.circuit.read = 1
    tester.circuit.write = 0
    tester.advance_cycle()
    tester.circuit.read = 1
    tester.circuit.write = 1
    tester.advance_cycle()
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})
    tester.circuit.read = 0
    tester.advance_cycle()
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@pytest.mark.parametrize("sva", [True, False])
def test_eventually(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        if sva:
            f.assert_(f.sva(io.write == 1, f"|-> s_eventually", io.write),
                      on=f.posedge(io.CLK))
        else:
            f.assert_((io.write == 1) | f.implies | f.eventually | io.read,
                      on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.write = 1
    tester.circuit.read = 0
    tester.advance_cycle()
    tester.circuit.write = 0
    for i in range(random.randint(3, 7)):
        tester.advance_cycle()
    # Read does not eventually go high
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out

    tester.circuit.read = 1
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})
