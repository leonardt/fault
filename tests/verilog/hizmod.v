module hizmod(
    input a,
    input b,
    output c
);

    tran ta(a, c);
    tran tb(b, c);

endmodule
