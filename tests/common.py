import shutil
import magma as m
import mantle


def pytest_sim_params(metafunc, *args, exclude=None):
    # set defaults
    if exclude is None:
        exclude = []
    elif isinstance(exclude, str):
        exclude = [exclude]
    exclude = set(exclude)

    # simulators supported by each kind of target
    sims_by_arg = {'system-verilog': ['vcs', 'ncsim', 'iverilog', 'vivado'],
                   'verilog-ams': ['ncsim'],
                   'verilator': [None],
                   'spice': ['ngspice', 'spectre', 'hspice']}

    # only parameterize if we can actually specify the target type
    # and simulator to use for this particular test
    fixturenames = metafunc.fixturenames
    if 'target' in fixturenames and 'simulator' in fixturenames:
        targets = []
        for arg in args:
            for simulator in sims_by_arg[arg]:
                if simulator in exclude:
                    continue
                elif simulator is None or shutil.which(simulator):
                    targets.append((arg, simulator))

        metafunc.parametrize("target,simulator", targets)


def outlines(capsys):
    captured = capsys.readouterr()
    lines = captured.out.splitlines()
    lines = [line.rstrip() for line in lines]
    return lines


def define_simple_circuit(T, circ_name, has_clk=False):
    class _Circuit(m.Circuit):
        __test__ = False   # Disable pytest discovery
        name = circ_name
        io = m.IO(I=m.In(T), O=m.Out(T))
        if has_clk:
            io += m.ClockIO()

        m.wire(io.I, io.O)

    return _Circuit


TestBasicCircuit = define_simple_circuit(m.Bit, "BasicCircuit")
TestArrayCircuit = define_simple_circuit(m.Array[3, m.Bit], "ArrayCircuit")
TestByteCircuit = define_simple_circuit(m.Bits[8], "ByteCircuit")
TestUInt32Circuit = define_simple_circuit(m.UInt[32], "UInt32Circuit")
TestUInt64Circuit = define_simple_circuit(m.UInt[64], "UInt64Circuit")
TestUInt128Circuit = define_simple_circuit(m.UInt[128], "UInt128Circuit")
TestSIntCircuit = define_simple_circuit(m.SInt[4], "SIntCircuit")
TestNestedArraysCircuit = define_simple_circuit(m.Array[3, m.Bits[4]],
                                                "NestedArraysCircuit")
TestDoubleNestedArraysCircuit = define_simple_circuit(
    m.Array[2, m.Array[3, m.Bits[4]]], "DoubleNestedArraysCircuit")
TestNestedArrayTupleCircuit = define_simple_circuit(
    m.Array[2, m.Array[3, m.Product.from_fields("anon", dict(a=m.Bits[4],
                                                             b=m.Bits[4]))]],
    "NestedArrayTupleCircuit")
TestBasicClkCircuit = define_simple_circuit(m.Bit, "BasicClkCircuit", True)
TestBasicClkCircuitCopy = define_simple_circuit(m.Bit, "BasicClkCircuitCopy",
                                                True)
TestTupleCircuit = define_simple_circuit(
    m.Product.from_fields("anon", dict(a=m.Bits[4], b=m.Bits[4])),
    "TupleCircuit")
TestNestedTupleCircuit = define_simple_circuit(
    m.Product.from_fields(
        "anon",
        dict(a=m.Product.from_fields("anon", dict(k=m.Bits[5], v=m.Bits[2])),
             b=m.Bits[4])),
    "NestedTupleCircuit")

T = m.Bits[3]


class TestPeekCircuit(m.Circuit):
    __test__ = False   # Disable pytest discovery
    io = m.IO(I=m.In(T), O0=m.Out(T), O1=m.Out(T))

    m.wire(io.I, io.O0)
    m.wire(io.I, io.O1)


class ConfigReg(m.Circuit):
    io = m.IO(D=m.In(m.Bits[2]), Q=m.Out(m.Bits[2])) + \
        m.ClockIO(has_ce=True)

    reg = mantle.Register(2, has_ce=True, name="conf_reg")
    io.Q @= reg(io.D, CE=io.CE)


class SimpleALU(m.Circuit):
    io = m.IO(a=m.In(m.UInt[16]),
              b=m.In(m.UInt[16]),
              c=m.Out(m.UInt[16]),
              config_data=m.In(m.Bits[2]),
              config_en=m.In(m.Enable),
              ) + m.ClockIO()

    opcode = ConfigReg(name="config_reg")(io.config_data, CE=io.config_en)
    io.c @= mantle.mux(
        # udiv not implemented
        # [io.a + io.b, io.a - io.b, io.a * io.b, io.a / io.b], opcode)
        # use arbitrary fourth op
        [io.a + io.b, io.a - io.b, io.a * io.b, io.b - io.a], opcode)


class AndCircuit(m.Circuit):
    io = m.IO(I0=m.In(m.Bit), I1=m.In(m.Bit), O=m.Out(m.Bit))

    io.O @= io.I0 & io.I1
