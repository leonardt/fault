module myblend(
    input real a,
    input real b,
    output real c
);

    assign c = (1.2 * b + 3.4 * a) / (1.2 + 3.4);

endmodule
