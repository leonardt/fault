import magma as m
from fault.verilogams import VAMSWrap, RealIn, RealOut


def test_vams_wrap():
    myblk = m.DeclareCircuit('myblk',
                             'a', RealIn,
                             'b', RealOut,
                             'c', m.In(m.Bit),
                             'd', m.Out(m.Bits[2]))
    wrap_circ = VAMSWrap(myblk)

    # check magma representation of wrapped circuit
    assert wrap_circ.IO.ports['a'] is RealIn
    assert wrap_circ.IO.ports['b'] is RealOut
    assert wrap_circ.IO.ports['c'] is m.In(m.Bit)
    assert wrap_circ.IO.ports['d'] is m.Out(m.Bits[2])

    # check Verilog-AMS code itself
    assert wrap_circ.vams_code == '''\
`include "disciplines.vams"

module myblk_wrap (
    input a,
    output b,
    input c,
    output d
);

    wreal a;
    wreal b;
    wire [0:0] c;
    wire [1:0] d;

    myblk myblk_inst (
        .a(a),
        .b(b),
        .c(c),
        .d(d)
    );

endmodule'''
