`include "myinv.v"

module mybuf_inc_test(
    input in_,
    output out
);

    wire out_n;

    myinv myinv_0 (.in_(in_), .out(out_n));
    myinv myinv_1 (.in_(out_n), .out(out));

endmodule
