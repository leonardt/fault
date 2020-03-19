`include "mLingua_pwl.vh"
`include "pwl_add2.v"

module mlingua_add (
    input pwl a_val,
    input pwl b_val,
    output pwl c_val
);


    real a_val_a;
    real a_val_b;
    real a_val_t;

    always @(*) begin
        a_val_a = a_val.a;
        a_val_b = a_val.b;
        a_val_t = a_val.t0;
    end

    pwl_add2 add2_inst(.in1(a_val), .in2(b_val),
        .scale1(1.0), .scale2(1.0),
        .out(c_val),
        .enable(1));

endmodule
