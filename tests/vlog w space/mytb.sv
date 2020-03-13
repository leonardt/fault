module mytb;
    reg in_;
    wire out;

    assign out = ~in_;

    task check(input stim, input expct); begin
        in_ = stim;
        #1;
        if (out !== expct) begin
            $error("Expected %0b, got %0b", expct, out);
        end
    end endtask

    initial begin
        check(1'b0, 1'b1);
        check(1'b1, 1'b0);
        $finish;
    end
endmodule
