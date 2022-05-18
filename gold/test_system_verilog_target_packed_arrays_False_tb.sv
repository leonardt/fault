`timescale 1ns/1ns
module test_system_verilog_target_packed_arrays_False_tb;

    reg [5:0] I [4:0][11:0][2:0];
    wire [5:0] O [4:0][11:0][2:0];

    

    test_system_verilog_target_packed_arrays_False #(
        
    ) dut (
        .I(I),
        .O(O)
    );

    initial begin


        #20 $finish;
    end

endmodule
