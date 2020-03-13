import magma as m
from fault.verilogams import VAMSWrap, RealIn, RealOut, ElectIn, ElectOut


def test_vams_wrap():
    # declare the circuit
    class myblk(m.Circuit):
        io = m.IO(
            a=RealIn,
            b=RealOut,
            c=m.In(m.Bit),
            d=m.Out(m.Bits[2]),
            e=ElectIn,
            f=ElectOut
        )
    wrap_circ = VAMSWrap(myblk)

    # check magma representation of wrapped circuit
    assert wrap_circ.IO.ports['a'] is RealIn
    assert wrap_circ.IO.ports['b'] is RealOut
    assert wrap_circ.IO.ports['c'] is m.In(m.Bit)
    assert wrap_circ.IO.ports['d'] is m.Out(m.Bits[2])
    assert wrap_circ.IO.ports['e'] is ElectIn
    assert wrap_circ.IO.ports['f'] is ElectOut

    # check Verilog-AMS code itself
    assert wrap_circ.vams_code == '''\
`include "disciplines.vams"

module myblk_wrap (
    input wreal a,
    output wreal b,
    input wire c,
    output wire [1:0] d,
    input electrical e,
    output electrical f
);

    myblk myblk_inst (
        .a(a),
        .b(b),
        .c(c),
        .d(d),
        .e(e),
        .f(f)
    );

endmodule
'''
