module myblk(
    input [3:0] a,
    output [3:0] b,
    input real c,
    output real d
);

    assign b = a + 4'd1;
    assign d = 1.23*c;

endmodule
