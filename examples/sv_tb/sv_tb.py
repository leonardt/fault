import random

import magma as m
import mantle
import fault


class Queue(m.Generator2):
    def __init__(self, T, entries, with_bug=False):
        assert entries >= 0
        self.io = m.IO(
            # Flipped since enq/deq is from perspective of the client
            enq=m.DeqIO[T],
            deq=m.EnqIO[T]
        ) + m.ClockIO()

        ram = m.Memory(entries, T)()
        enq_ptr = mantle.CounterModM(entries, entries.bit_length(),
                                     has_ce=True, cout=False)
        deq_ptr = mantle.CounterModM(entries, entries.bit_length(),
                                     has_ce=True, cout=False)
        maybe_full = m.Register(init=False, has_enable=True)()

        ptr_match = enq_ptr.O == deq_ptr.O
        empty = ptr_match & ~maybe_full.O
        if with_bug:
            # never full
            full = False
        else:
            full = ptr_match & maybe_full.O

        self.io.deq.valid @= ~empty
        self.io.enq.ready @= ~full

        do_enq = self.io.enq.fired()
        do_deq = self.io.deq.fired()

        ram.write(self.io.enq.data, enq_ptr.O[:-1], m.enable(do_enq))

        enq_ptr.CE @= m.enable(do_enq)
        deq_ptr.CE @= m.enable(do_deq)

        maybe_full.I @= m.enable(do_enq)
        maybe_full.CE @= m.enable(do_enq != do_deq)
        self.io.deq.data @= ram[deq_ptr.O[:-1]]

        def ispow2(n):
            return (n & (n - 1) == 0) and n != 0


def test_queue(with_bug):
    T = m.Bits[8]
    Queue4x8 = Queue(T, 4, with_bug=with_bug)

    class Monitor(m.Circuit):
        io = m.IO(
            enq=m.In(m.ReadyValid[T]),
            deq=m.In(m.ReadyValid[T])
        ) + m.ClockIO()
        m.inline_verilog("""\
reg [7:0] data [0:3];
reg [2:0] write_pointer;
reg [2:0] read_pointer;
wire wen;
wire ren;
wire full;
wire empty;
assign wen = {io.enq.valid} & {io.enq.ready};
assign ren = {io.deq.ready} & {io.deq.valid};
assign empty = write_pointer == read_pointer;
assign full = ((write_pointer[1:0] == read_pointer[1:0]) &
               (write_pointer[2] == ~read_pointer[2]));
always @(posedge {io.CLK}) begin
    if (wen) begin
        assert (!full) else $error("Trying to write to full buffer");
        data[write_pointer[1:0]] <= {io.enq.data};
        write_pointer <= write_pointer + 1;
    end
    if (ren) begin
        assert (!empty) else $error("Trying to read from empty buffer");
        assert ({io.deq.data} == data[read_pointer[1:0]]) else
            $error("Got wrong read data: io.deq.data %x != %x",
                   {io.deq.data}, data[read_pointer[1:0]]);
        read_pointer <= read_pointer + 1;
    end
end""")

    class DUT(m.Circuit):
        io = m.IO(
            enq=m.DeqIO[T],
            deq=m.EnqIO[T],
        ) + m.ClockIO()
        queue = Queue4x8()
        queue.enq @= io.enq
        queue.deq @= io.deq

        monitor = Monitor()
        monitor.enq.valid @= io.enq.valid
        monitor.enq.data @= io.enq.data
        monitor.enq.ready @= queue.enq.ready

        monitor.deq.valid @= queue.deq.valid
        monitor.deq.data @= queue.deq.data
        monitor.deq.ready @= io.deq.ready

    tester = fault.SynchronousTester(DUT, DUT.CLK)
    data = [0xDE, 0xAD, 0xBE, 0xEF]
    for i in range(32):
        tester.circuit.enq.data = random.choice(data)
        tester.circuit.enq.valid = random.randint(0, 1)
        tester.circuit.deq.ready = random.randint(0, 1)
        tester.advance_cycle()
    try:
        tester.compile_and_run("verilator", flags=["--assert"],
                               magma_opts={"inline": True})
        assert not with_bug
    except AssertionError:
        assert with_bug


test_queue(True)

# Need to reset between test runs
m.frontend.coreir_.ResetCoreIR()
m.generator.reset_generator_cache()
test_queue(False)
