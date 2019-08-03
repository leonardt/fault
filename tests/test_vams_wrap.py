import magma as m
from fault.verilogams import VAMSWrap, AnalogIn, AnalogOut


def test_vams_wrap():
    myblk = m.DeclareCircuit('myblk',
                             'a', AnalogIn,
                             'b', AnalogOut,
                             'c', m.In(m.Bit),
                             'd', m.Out(m.Bits[2]))
    wrap_circ = VAMSWrap(myblk)

    # check magma representation of wrapped circuit
    assert wrap_circ.IO.ports['a'] is AnalogIn
    assert wrap_circ.IO.ports['b'] is AnalogOut
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

    electrical a;
    electrical b;
    wire [0:0] c;
    wire [1:0] d;

    myblk myblk_inst (
        .a(a),
        .b(b),
        .c(c),
        .d(d)
    );

endmodule'''
