`ifdef __IVERILOG__
    `define real_t wire real
`endif

`ifndef real_t
    `define real_t real
`endif

module realadd (
    input `real_t a_val,
    input `real_t b_val,
    output `real_t c_val
);

    assign c_val = a_val + b_val;

endmodule
