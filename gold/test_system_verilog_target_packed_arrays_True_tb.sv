`timescale 1ns/1ns
module test_system_verilog_target_packed_arrays_True_tb;

    reg [4:0][11:0][2:0] [5:0] I;
    wire [4:0][11:0][2:0] [5:0] O;

    

    test_system_verilog_target_packed_arrays_True #(
        
    ) dut (
        .I(I),
        .O(O)
    );

    initial begin


        #20 $finish;
    end

endmodule
