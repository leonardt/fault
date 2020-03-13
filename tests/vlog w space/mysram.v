module mysram(
    input wl,
    inout lbl,
    inout lblb
);

    // internal capacitive nodes
    reg lbl_x, lblb_x;
    bufif1 (weak1, weak0) ba (lbl, lbl_x, wl);
    bufif1 (weak1, weak0) bb (lblb, lblb_x, wl);

    // writing internal nodes
    always @(wl or lbl or lblb) begin
        #0;
        if (wl == 1'b1) begin
            lbl_x = lbl;
            lblb_x = lblb;
        end
    end

endmodule
