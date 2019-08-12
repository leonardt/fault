module mysram(
    input wl,
    inout lbl,
    inout lblb
);

    // internal capacitive nodes
    reg lbl_x, lblb_x;
    assign (weak1, weak0) lbl = wl ? lbl_x : 1'bz;
    assign (weak1, weak0) lblb = wl ? lblb_x : 1'bz;

    // writing internal nodes
    always @(wl or lbl or lblb) begin
        if (wl == 1'b1) begin
            lbl_x = lbl;
            lblb_x = lblb;
        end
    end

endmodule
