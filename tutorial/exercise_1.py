import magma as m


class ConfigReg(m.Circuit):
    io = m.IO(D=m.In(m.Bits[2]), Q=m.Out(m.Bits[2])) + \
        m.ClockIO(has_ce=True)

    reg = m.Register(m.Bits[2], has_enable=True)(name="config_reg")
    io.Q <= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              c=m.Out(m.UInt[16]),
              config_data=m.In(m.Bits[2]),
              config_en=m.In(m.Enable),
              ) + m.ClockIO()

    opcode = ConfigReg(name="opcode_reg")(io.config_data, CE=io.config_en)
    io.c <= m.mux(
        [io.a + io.b, io.a - io.b, io.a * io.b, io.b - io.a], opcode)
