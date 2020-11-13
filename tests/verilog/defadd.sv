module defadd #(
    parameter integer n_bits=`N_BITS,
    parameter integer b_val=`B_VAL
) (
    input wire logic [n_bits-1:0] a_val,
    output wire logic [n_bits-1:0] c_val
);

    /* verilator lint_off WIDTH */
    assign c_val = a_val + b_val;
    /* verilator lint_on WIDTH */

endmodule
