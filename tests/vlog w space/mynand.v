module mynand(
    input a,
    input b,
    output out
);

    assign out = ~(a & b);

endmodule
