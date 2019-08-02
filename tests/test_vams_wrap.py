import magma as m
from fault.verilogams import VerilogAMSWrapper, AnalogIn, AnalogOut


def test_vams_wrap():
    myblk = m.DeclareCircuit('myblk',
                             'a', AnalogIn,
                             'b', AnalogOut,
                             'c', m.In(m.Bit),
                             'd', m.Out(m.Bits[2]))
    wrapper = VerilogAMSWrapper(myblk)

    assert wrapper.generate_code() == '''\
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
