import shutil
import random
import os

import pytest
import decorator
import fault as f
import magma as m
from hwtypes import BitVector


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


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_eventually(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(write=m.In(m.Bit), read=m.In(m.Bit)) + m.ClockIO()
        if sva:
            f.assert_(f.sva(io.write == 1, f"|-> s_eventually", io.read == 1),
                      on=f.posedge(io.CLK))
        else:
            f.assert_((io.write == 1) | f.implies | f.eventually |
                      (io.read == 1), on=f.posedge(io.CLK))

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


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_throughout(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bit), b=m.In(m.Bit), c=m.In(m.Bit)) + m.ClockIO()
        if sva:
            seq = f.sva(io.b, "throughout", "!", io.c, "[-> 1]")
            f.assert_(f.sva(f.rose(io.a), "|->", seq),
                      on=f.posedge(io.CLK))
        else:
            seq = io.b | f.throughout | f.not_(io.c | f.goto[1])
            f.assert_(f.rose(io.a) | f.implies | seq,
                      on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b high until c goes low
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    for i in range(random.randint(3, 7)):
        tester.advance_cycle()
    tester.circuit.c = 0
    tester.advance_cycle()
    tester.circuit.b = 0

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b not high until c goes low
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    tester.circuit.b = 0
    tester.advance_cycle()

    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_until(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bit), b=m.In(m.Bit), c=m.In(m.Bit)) + m.ClockIO()
        if sva:
            seq = f.sequence(f.sva(io.b, "until !", io.c))
            f.assert_(f.sva(f.rose(io.a), "|->", seq), on=f.posedge(io.CLK))
        else:
            seq = f.sequence(io.b | f.until | f.not_(io.c))
            f.assert_(f.rose(io.a) | f.implies | seq, on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b high until 1 cycle before c goes low
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    for i in range(random.randint(3, 7)):
        tester.advance_cycle()
    tester.circuit.b = 0
    tester.circuit.c = 0
    tester.advance_cycle()

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b goes low two cycles before c
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    tester.advance_cycle()
    tester.circuit.b = 0
    tester.advance_cycle()
    tester.advance_cycle()
    tester.circuit.c = 0

    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_until_with(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bit), b=m.In(m.Bit), c=m.In(m.Bit)) + m.ClockIO()
        if sva:
            seq = f.sequence(f.sva(io.b, "until_with !", io.c))
            f.assert_(f.sva(f.rose(io.a), "|->", seq), on=f.posedge(io.CLK))
        else:
            seq = f.sequence(io.b | f.until_with | f.not_(io.c))
            f.assert_(f.rose(io.a) | f.implies | seq, on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b high until the cycle c goes low
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    for i in range(random.randint(3, 7)):
        tester.advance_cycle()
    tester.circuit.c = 0
    tester.advance_cycle()
    tester.circuit.b = 0
    tester.advance_cycle()

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.circuit.c = 1
    tester.advance_cycle()
    # Posedge a, b goes low before c
    tester.circuit.a = 1
    tester.circuit.b = 1
    tester.advance_cycle()
    tester.advance_cycle()
    tester.circuit.b = 0
    tester.advance_cycle()
    tester.circuit.c = 0
    tester.advance_cycle()

    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@requires_ncsim
@pytest.mark.parametrize("sva", [True, False])
def test_inside(sva, capsys):
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bits[2])) + m.ClockIO()
        if sva:
            f.assert_(f.sva(io.a, "inside {0, 1}"), on=f.posedge(io.CLK))
        else:
            f.assert_(io.a | f.inside | {0, 1}, on=f.posedge(io.CLK))

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 0
    tester.advance_cycle()
    tester.circuit.a = 1
    tester.advance_cycle()

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.a = 2
    tester.advance_cycle()

    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.__assert_1 has failed" in out


@requires_ncsim
def test_disable_if():
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bit), b=m.In(m.Bit))
        io += m.ClockIO(has_resetn=True)
        f.assert_(io.a | f.implies | f.delay[2] | io.b, on=f.posedge(io.CLK),
                  disable_iff=f.not_(io.RESETN))
        f.assert_(f.sva(io.a, "|-> ##2", io.b), on=f.posedge(io.CLK),
                  disable_iff=f.not_(io.RESETN))
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.RESETN = 1
    tester.circuit.a = 1
    tester.advance_cycle()
    tester.circuit.a = 0
    tester.advance_cycle()
    tester.circuit.b = 1
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.RESETN = 1
    tester.circuit.a = 1
    tester.advance_cycle()
    tester.circuit.a = 0
    tester.advance_cycle()
    tester.circuit.RESETN = 0
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.RESETN = 1
    tester.circuit.a = 1
    tester.advance_cycle()
    tester.circuit.a = 0
    tester.advance_cycle()
    tester.advance_cycle()
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})


@requires_ncsim
@pytest.mark.parametrize('compile_guard', ["ASSERT_ON",
                                           ["ASSERT_ON", "FORMAL_ON"]])
def test_ifdef_and_name(capsys, compile_guard):
    class Main(m.Circuit):
        io = m.IO(a=m.In(m.Bit), b=m.In(m.Bit))
        io += m.ClockIO(has_resetn=True)
        f.assert_(io.a | f.implies | f.delay[2] | io.b, on=f.posedge(io.CLK),
                  disable_iff=f.not_(io.RESETN), compile_guard=compile_guard,
                  name="foo")
        temp = m.Bit(name="temp")
        temp @= io.a
        f.assert_(f.sva(temp, "|-> ##2", io.b), on=f.posedge(io.CLK),
                  disable_iff=f.not_(io.RESETN), compile_guard=compile_guard,
                  name="bar")

    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.RESETN = 1
    tester.circuit.a = 1
    tester.advance_cycle()
    tester.circuit.a = 0
    tester.advance_cycle()
    tester.advance_cycle()
    # Should not fail with no ASSERT_ON
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True})
    # Check that wire prefix is generated properly
    with open("build/Main.v", "r") as file_:
        assert "wire _FAULT_ASSERT_WIRE_0" in file_.read()
    # Should fail
    with pytest.raises(AssertionError):
        if isinstance(compile_guard, str):
            compile_guard = [compile_guard]
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"] +
                               [f"+define+{guard}" for guard in compile_guard],
                               magma_opts={"inline": True})
    out, _ = capsys.readouterr()
    assert "Assertion Main_tb.dut.foo has failed" in out
    assert "Assertion Main_tb.dut.bar has failed" in out


@requires_ncsim
def test_default_clock_function():
    def my_assert(property, on=None, disable_iff=None):
        # If needed, create undriven clock/reset temporaries, will be driven by
        # automatic clock wiring logic
        if on is None:
            on = f.posedge(m.Clock())
        if disable_iff is None:
            disable_iff = f.not_(m.AsyncResetN())
        f.assert_(property, on=on, disable_iff=disable_iff)

    class ClockIntf(m.Product):
        clock = m.In(m.Clock)
        reset = m.In(m.AsyncResetN)

    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bits[8]), O=m.Out(m.Bits[8]))
        io += m.IO(clocks=ClockIntf)
        io.O @= m.Register(T=m.Bits[8], reset_type=m.AsyncResetN)()(io.I)
        my_assert(io.I | f.implies | f.delay[1] | io.O)

    tester = f.SynchronousTester(Main, Main.clocks.clock)
    I_seq = [1, 0, 1, 0, 0]
    O_seq = [1, 0, 1, 0, 0]
    tester.circuit.clocks.reset = 1
    for I, O in zip(I_seq, O_seq):
        tester.circuit.I = I
        tester.advance_cycle()
        tester.circuit.O.expect(O)
    # Should disable during reset
    tester.circuit.I = 1
    tester.circuit.clocks.reset = 0
    tester.advance_cycle()
    tester.circuit.O.expect(0)

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True,
                                                      "drive_undriven": True,
                                                      "terminate_unused": True})


@requires_ncsim
def test_cover(capsys):
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit)) + m.ClockIO()
        io.O @= m.Register(T=m.Bit)()(io.I)
        f.cover(io.I | f.delay[1] | ~io.I, on=f.posedge(io.CLK))
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True},
                           disp_type="realtime", coverage=True)

    out, _ = capsys.readouterr()
    # not covered
    assert """\
  Disabled Finish Failed   Assertion Name
         0      0      0   Main_tb.dut.__cover1
  Total Assertions = 1,  Failing Assertions = 0,  Unchecked Assertions = 1\
""" in out
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 0
    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True},
                           disp_type="realtime", coverage=True)

    out, _ = capsys.readouterr()
    # covered
    assert """\
  Disabled Finish Failed   Assertion Name
         0      1      0   Main_tb.dut.__cover1
  Total Assertions = 1,  Failing Assertions = 0,  Unchecked Assertions = 0\
""" in out


@requires_ncsim
def test_assume(capsys):
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bit), O=m.Out(m.Bit)) + m.ClockIO()
        io.O @= m.Register(T=m.Bit)()(io.I)
        f.assume(io.I | f.delay[1] | ~io.I, on=f.posedge(io.CLK))
    tester = f.SynchronousTester(Main, Main.CLK)
    tester.circuit.I = 1
    tester.advance_cycle()
    tester.circuit.I = 1
    tester.advance_cycle()
    # assume behaves like assert in simulation (but used as an assumption for
    # formal tools)
    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"], magma_opts={"inline": True})


@requires_ncsim
@pytest.mark.parametrize('use_sva', [False, True])
def test_not_onehot(use_sva):
    class Main(m.Circuit):
        io = m.IO(I=m.In(m.Bits[8]), x=m.In(m.Bit)) + m.ClockIO()
        if use_sva:
            f.assert_(f.sva(f.not_(f.onehot(io.I)), "|-> ##1", io.x),
                      on=f.posedge(io.CLK))
        else:
            f.assert_(f.not_(f.onehot(io.I)) | f.implies | f.delay[1] | io.x,
                      on=f.posedge(io.CLK))

    tester = f.Tester(Main, Main.CLK)
    tester.circuit.I = 0xFF
    tester.step(2)
    tester.circuit.x = True
    tester.circuit.I = 0x80
    tester.step(2)
    tester.circuit.I = 0x0
    tester.circuit.x = False
    tester.step(2)

    tester.compile_and_run("system-verilog", simulator="ncsim",
                           flags=["-sv"], magma_opts={"inline": True,
                                                      "drive_undriven": True,
                                                      "terminate_unused": True})

    tester.circuit.I = 0xFF
    tester.step(2)
    tester.circuit.x = 0
    tester.step(2)

    with pytest.raises(AssertionError):
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"],
                               magma_opts={"inline": True,
                                           "drive_undriven": True,
                                           "terminate_unused": True})


@requires_ncsim
@pytest.mark.parametrize('use_sva', [True, False])
@pytest.mark.parametrize('should_pass', [True, False])
def test_advanced_property_example_1(use_sva, should_pass):
    class Foo(m.Circuit):
        io = m.IO(a=m.In(m.Bits[8]), b=m.In(m.Bits[8]), c=m.In(m.Bits[8]),
                  x=m.Out(m.Bits[8]), y=m.Out(m.Bits[8]))
        io += m.ClockIO(has_resetn=True)
        x = [m.bits(0, 8), m.bits(0, 8), m.bits(1, 8), m.bits(0, 8)]
        if should_pass:
            y = [m.bits(0, 8), m.bits(1, 8), m.bits(2, 8), m.bits(3, 8)]
        else:
            y = [m.bits(1, 8), m.bits(1, 8), m.bits(1, 8), m.bits(1, 8)]
        count = m.Register(m.Bits[2])()
        count.I @= count.O + 1
        io.x @= m.mux(x, count.O)
        io.y @= m.mux(y, count.O)
        m.display("io.x=%x, io.y=%x", io.x, io.y).when(m.posedge(io.CLK))
        if use_sva:
            f.assert_(
                f.sva(f.not_(f.onehot(io.a)), "&&",
                      io.b.reduce_or(), "&&",
                      io.x[0].value(), "|=>",
                      io.y.value() != f.past(io.y.value(), 2)),
                name="name_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )
        else:
            f.assert_(
                # Note parens matter!
                (f.not_(f.onehot(io.a)) & io.b.reduce_or() & io.x[0].value())
                | f.implies | f.delay[1] |
                (io.y.value() != f.past(io.y.value(), 2)),
                name="name_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )

    tester = f.Tester(Foo, Foo.CLK)
    tester.circuit.RESETN = 1
    # not onehot a
    tester.circuit.a = 0xEF
    # at least one bit set on b
    tester.circuit.b = 0x70
    tester.step(2)
    tester.step(2)
    tester.step(2)
    tester.step(2)
    try:
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"],
                               magma_opts={"inline": True,
                                           "drive_undriven": True,
                                           "terminate_unused": True})
        assert should_pass
    except AssertionError:
        assert not should_pass


@requires_ncsim
@pytest.mark.parametrize('use_sva', [True, False])
@pytest.mark.parametrize('should_pass', [True, False])
def test_advanced_property_example_2(use_sva, should_pass):
    class Foo(m.Circuit):
        io = m.IO(valid=m.In(m.Bit), sop=m.In(m.Bit), eop=m.In(m.Bit),
                  ready=m.Out(m.Bit)) + m.ClockIO(has_resetn=True)
        io.ready @= 1
        if use_sva:
            f.assert_(
                f.sva(f.not_(~(io.valid & io.ready.value() & io.eop)),
                      "throughout",
                      # Note: need sequence here to wrap parens
                      f.sequence(f.sva((io.valid & io.ready.value() & io.sop),
                                       "[-> 2]"))),
                name="eop_must_happen_btn_two_sop_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )
            f.assert_(
                f.sva(io.valid & io.ready.value() & io.eop, "##1",
                      ~io.valid, "[*0:$] ##1", io.valid, "|->", io.sop),
                name="first_valid_after_eop_must_have_sop_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )
        else:
            f.assert_(
                f.not_(~(io.valid & io.ready.value() & io.eop))
                | f.throughout |
                ((io.valid & io.ready.value() & io.sop) | f.goto[2]),
                name="eop_must_happen_btn_two_sop_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )
            f.assert_(
                (io.valid & io.ready.value() & io.eop) | f.delay[1] |
                (~io.valid) | f.repeat[0:] | f.delay[1] |
                (io.valid | f.implies | io.sop),
                name="first_valid_after_eop_must_have_sop_A",
                on=f.posedge(io.CLK),
                disable_iff=f.not_(io.RESETN)
            )

    tester = f.Tester(Foo, Foo.CLK)
    tester.circuit.RESETN = 1
    tester.circuit.valid = 1
    tester.circuit.eop = 1
    tester.circuit.sop = 1
    tester.step(2)
    if not should_pass:
        tester.circuit.sop = 0
    tester.step(2)
    try:
        tester.compile_and_run("system-verilog", simulator="ncsim",
                               flags=["-sv"],
                               magma_opts={"inline": True,
                                           "drive_undriven": True,
                                           "terminate_unused": True})
    except AssertionError:
        assert not should_pass
    else:
        assert should_pass
