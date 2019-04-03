import magma as m
import mantle
import fault
from reset_tester import ResetTester


data_width = 16
addr_width = 4

# Randomize initial contents of memory
init = [fault.random.random_bv(data_width) for _ in range(1 << addr_width)]


class ROM(m.Circuit):
    IO = [
        "RADDR", m.In(m.Bits[addr_width]),
        "RDATA", m.Out(m.Bits[data_width]),
        "CLK", m.In(m.Clock)
    ]

    @classmethod
    def definition(io):
        regs = [mantle.Register(data_width, init=init[i])
                for i in range(1 << addr_width)]
        for reg in regs:
            reg.I <= reg.O
        io.RDATA <= mantle.mux([reg.O for reg in regs], io.RADDR)


class RAM(m.Circuit):
    IO = [
        "RADDR", m.In(m.Bits[addr_width]),
        "RDATA", m.Out(m.Bits[data_width]),
        "WADDR", m.In(m.Bits[addr_width]),
        "WDATA", m.In(m.Bits[data_width]),
        "WE", m.In(m.Bit),
        "CLK", m.In(m.Clock)
    ]

    @classmethod
    def definition(io):
        regs = [mantle.Register(data_width, init=init[i], has_ce=True)
                for i in range(1 << addr_width)]
        for i, reg in enumerate(regs):
            reg.I <= io.WDATA
            reg.CE <= (io.WADDR == m.bits(i, addr_width)) & io.WE
        io.RDATA <= mantle.mux([reg.O for reg in regs], io.RADDR)
