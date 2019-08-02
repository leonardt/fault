from fault.verilogams import (VerilogAMSWrapper,
                              AnalogVAMSPort,
                              DigitalVAMSPort)


def test_vams_wrap():
    ports = [AnalogVAMSPort('a', 'input'),
             AnalogVAMSPort('b', 'output'),
             DigitalVAMSPort('c', 'input'),
             DigitalVAMSPort('d', 'output', width=2)]
    wrapper = VerilogAMSWrapper(mod_name='myblk', ports=ports)

    assert wrapper.generate_code() == '''\
`include "disciplines.vams"

module myblk_wrapper (
    input a,
    output b,
    input c,
    output d
);

    electrical a;
    electrical b;
    wire c;
    wire [1:0] d;

    myblk myblk_inst (
        .a(a),
        .b(b),
        .c(c),
        .d(d)
    );

endmodule'''
