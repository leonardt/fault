module mysram(
    input wl,
    inout lbl,
    inout lblb
);

    // internal capacitive nodes
    trireg lbl_x, lblb_x;

    // access switches
    tranif1 sa (lbl, lbl_x, wl);
    tranif1 sb (lblb, lblb_x, wl);

endmodule
