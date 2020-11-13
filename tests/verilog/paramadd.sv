module paramadd #(
    parameter integer n_bits=1,
    parameter integer b_val=0
) (
    input wire logic [n_bits-1:0] a_val,
    output wire logic [n_bits-1:0] c_val
);

    /* verilator lint_off WIDTH */
    assign c_val = a_val + b_val;
    /* verilator lint_on WIDTH */

endmodule
