module extra_module #(
    parameter file_name="file.mem"
) (
    input [1:0] addr,
    output [2:0] data
);
    // read into rom
    reg [2:0] rom [0:3];
    initial begin
        $readmemb(file_name, rom);
    end
    // assign to output
    assign data=rom[addr];
endmodule

module myinv(
    input in_,
    output out
);
    assign out = ~in_;
endmodule
