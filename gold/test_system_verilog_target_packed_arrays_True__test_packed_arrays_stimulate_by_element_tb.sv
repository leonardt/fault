`timescale 1ns/1ns
module test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element_tb;

    reg [4:0][11:0][2:0] [5:0] I;
    wire [4:0][11:0][2:0] [5:0] O;

    

    test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element #(
        
    ) dut (
        .I(I),
        .O(O)
    );

    initial begin
        I[3][6][0] <= 6'd33;
        #1;
        if (!(O[3][6][0] === 6'd33)) begin
            $error("Failed on action=2 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][6][0].  Expected %x, got %x.", 6'd33, O[3][6][0]);
        end
        I[4][7][1] <= 6'd38;
        #1;
        if (!(O[4][7][1] === 6'd38)) begin
            $error("Failed on action=5 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][1].  Expected %x, got %x.", 6'd38, O[4][7][1]);
        end
        I[3][5][2] <= 6'd27;
        #1;
        if (!(O[3][5][2] === 6'd27)) begin
            $error("Failed on action=8 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][5][2].  Expected %x, got %x.", 6'd27, O[3][5][2]);
        end
        I[4][2][1] <= 6'd17;
        #1;
        if (!(O[4][2][1] === 6'd17)) begin
            $error("Failed on action=11 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][2][1].  Expected %x, got %x.", 6'd17, O[4][2][1]);
        end
        I[0][9][1] <= 6'd18;
        #1;
        if (!(O[0][9][1] === 6'd18)) begin
            $error("Failed on action=14 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][9][1].  Expected %x, got %x.", 6'd18, O[0][9][1]);
        end
        I[2][1][2] <= 6'd9;
        #1;
        if (!(O[2][1][2] === 6'd9)) begin
            $error("Failed on action=17 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][1][2].  Expected %x, got %x.", 6'd9, O[2][1][2]);
        end
        I[2][7][2] <= 6'd12;
        #1;
        if (!(O[2][7][2] === 6'd12)) begin
            $error("Failed on action=20 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][7][2].  Expected %x, got %x.", 6'd12, O[2][7][2]);
        end
        I[2][6][1] <= 6'd26;
        #1;
        if (!(O[2][6][1] === 6'd26)) begin
            $error("Failed on action=23 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][6][1].  Expected %x, got %x.", 6'd26, O[2][6][1]);
        end
        I[4][7][1] <= 6'd33;
        #1;
        if (!(O[4][7][1] === 6'd33)) begin
            $error("Failed on action=26 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][1].  Expected %x, got %x.", 6'd33, O[4][7][1]);
        end
        I[0][8][0] <= 6'd11;
        #1;
        if (!(O[0][8][0] === 6'd11)) begin
            $error("Failed on action=29 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][8][0].  Expected %x, got %x.", 6'd11, O[0][8][0]);
        end
        I[3][11][2] <= 6'd0;
        #1;
        if (!(O[3][11][2] === 6'd0)) begin
            $error("Failed on action=32 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][11][2].  Expected %x, got %x.", 6'd0, O[3][11][2]);
        end
        I[4][7][1] <= 6'd31;
        #1;
        if (!(O[4][7][1] === 6'd31)) begin
            $error("Failed on action=35 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][1].  Expected %x, got %x.", 6'd31, O[4][7][1]);
        end
        I[2][11][0] <= 6'd24;
        #1;
        if (!(O[2][11][0] === 6'd24)) begin
            $error("Failed on action=38 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][11][0].  Expected %x, got %x.", 6'd24, O[2][11][0]);
        end
        I[4][3][0] <= 6'd18;
        #1;
        if (!(O[4][3][0] === 6'd18)) begin
            $error("Failed on action=41 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][3][0].  Expected %x, got %x.", 6'd18, O[4][3][0]);
        end
        I[4][7][0] <= 6'd10;
        #1;
        if (!(O[4][7][0] === 6'd10)) begin
            $error("Failed on action=44 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][0].  Expected %x, got %x.", 6'd10, O[4][7][0]);
        end
        I[2][8][1] <= 6'd13;
        #1;
        if (!(O[2][8][1] === 6'd13)) begin
            $error("Failed on action=47 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][8][1].  Expected %x, got %x.", 6'd13, O[2][8][1]);
        end
        I[2][8][1] <= 6'd15;
        #1;
        if (!(O[2][8][1] === 6'd15)) begin
            $error("Failed on action=50 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][8][1].  Expected %x, got %x.", 6'd15, O[2][8][1]);
        end
        I[4][5][2] <= 6'd26;
        #1;
        if (!(O[4][5][2] === 6'd26)) begin
            $error("Failed on action=53 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][5][2].  Expected %x, got %x.", 6'd26, O[4][5][2]);
        end
        I[4][8][2] <= 6'd36;
        #1;
        if (!(O[4][8][2] === 6'd36)) begin
            $error("Failed on action=56 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][8][2].  Expected %x, got %x.", 6'd36, O[4][8][2]);
        end
        I[3][1][2] <= 6'd49;
        #1;
        if (!(O[3][1][2] === 6'd49)) begin
            $error("Failed on action=59 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][1][2].  Expected %x, got %x.", 6'd49, O[3][1][2]);
        end
        I[2][9][0] <= 6'd37;
        #1;
        if (!(O[2][9][0] === 6'd37)) begin
            $error("Failed on action=62 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][9][0].  Expected %x, got %x.", 6'd37, O[2][9][0]);
        end
        I[1][3][0] <= 6'd4;
        #1;
        if (!(O[1][3][0] === 6'd4)) begin
            $error("Failed on action=65 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][3][0].  Expected %x, got %x.", 6'd4, O[1][3][0]);
        end
        I[4][10][1] <= 6'd60;
        #1;
        if (!(O[4][10][1] === 6'd60)) begin
            $error("Failed on action=68 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][10][1].  Expected %x, got %x.", 6'd60, O[4][10][1]);
        end
        I[0][1][2] <= 6'd16;
        #1;
        if (!(O[0][1][2] === 6'd16)) begin
            $error("Failed on action=71 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][1][2].  Expected %x, got %x.", 6'd16, O[0][1][2]);
        end
        I[1][0][0] <= 6'd50;
        #1;
        if (!(O[1][0][0] === 6'd50)) begin
            $error("Failed on action=74 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][0][0].  Expected %x, got %x.", 6'd50, O[1][0][0]);
        end
        I[4][4][2] <= 6'd30;
        #1;
        if (!(O[4][4][2] === 6'd30)) begin
            $error("Failed on action=77 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][4][2].  Expected %x, got %x.", 6'd30, O[4][4][2]);
        end
        I[1][10][2] <= 6'd53;
        #1;
        if (!(O[1][10][2] === 6'd53)) begin
            $error("Failed on action=80 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][10][2].  Expected %x, got %x.", 6'd53, O[1][10][2]);
        end
        I[4][4][1] <= 6'd63;
        #1;
        if (!(O[4][4][1] === 6'd63)) begin
            $error("Failed on action=83 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][4][1].  Expected %x, got %x.", 6'd63, O[4][4][1]);
        end
        I[2][1][1] <= 6'd14;
        #1;
        if (!(O[2][1][1] === 6'd14)) begin
            $error("Failed on action=86 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][1][1].  Expected %x, got %x.", 6'd14, O[2][1][1]);
        end
        I[3][9][2] <= 6'd42;
        #1;
        if (!(O[3][9][2] === 6'd42)) begin
            $error("Failed on action=89 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][9][2].  Expected %x, got %x.", 6'd42, O[3][9][2]);
        end
        I[1][3][0] <= 6'd34;
        #1;
        if (!(O[1][3][0] === 6'd34)) begin
            $error("Failed on action=92 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][3][0].  Expected %x, got %x.", 6'd34, O[1][3][0]);
        end
        I[0][11][0] <= 6'd47;
        #1;
        if (!(O[0][11][0] === 6'd47)) begin
            $error("Failed on action=95 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][11][0].  Expected %x, got %x.", 6'd47, O[0][11][0]);
        end
        I[1][5][1] <= 6'd7;
        #1;
        if (!(O[1][5][1] === 6'd7)) begin
            $error("Failed on action=98 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][5][1].  Expected %x, got %x.", 6'd7, O[1][5][1]);
        end
        I[0][2][2] <= 6'd28;
        #1;
        if (!(O[0][2][2] === 6'd28)) begin
            $error("Failed on action=101 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][2][2].  Expected %x, got %x.", 6'd28, O[0][2][2]);
        end
        I[0][9][2] <= 6'd9;
        #1;
        if (!(O[0][9][2] === 6'd9)) begin
            $error("Failed on action=104 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][9][2].  Expected %x, got %x.", 6'd9, O[0][9][2]);
        end
        I[0][1][2] <= 6'd24;
        #1;
        if (!(O[0][1][2] === 6'd24)) begin
            $error("Failed on action=107 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][1][2].  Expected %x, got %x.", 6'd24, O[0][1][2]);
        end
        I[4][9][0] <= 6'd50;
        #1;
        if (!(O[4][9][0] === 6'd50)) begin
            $error("Failed on action=110 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][9][0].  Expected %x, got %x.", 6'd50, O[4][9][0]);
        end
        I[0][5][0] <= 6'd4;
        #1;
        if (!(O[0][5][0] === 6'd4)) begin
            $error("Failed on action=113 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][5][0].  Expected %x, got %x.", 6'd4, O[0][5][0]);
        end
        I[4][0][0] <= 6'd23;
        #1;
        if (!(O[4][0][0] === 6'd23)) begin
            $error("Failed on action=116 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][0][0].  Expected %x, got %x.", 6'd23, O[4][0][0]);
        end
        I[0][7][0] <= 6'd7;
        #1;
        if (!(O[0][7][0] === 6'd7)) begin
            $error("Failed on action=119 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][7][0].  Expected %x, got %x.", 6'd7, O[0][7][0]);
        end
        I[0][8][1] <= 6'd12;
        #1;
        if (!(O[0][8][1] === 6'd12)) begin
            $error("Failed on action=122 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][8][1].  Expected %x, got %x.", 6'd12, O[0][8][1]);
        end
        I[2][1][0] <= 6'd9;
        #1;
        if (!(O[2][1][0] === 6'd9)) begin
            $error("Failed on action=125 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][1][0].  Expected %x, got %x.", 6'd9, O[2][1][0]);
        end
        I[2][5][1] <= 6'd23;
        #1;
        if (!(O[2][5][1] === 6'd23)) begin
            $error("Failed on action=128 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][5][1].  Expected %x, got %x.", 6'd23, O[2][5][1]);
        end
        I[0][8][1] <= 6'd5;
        #1;
        if (!(O[0][8][1] === 6'd5)) begin
            $error("Failed on action=131 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][8][1].  Expected %x, got %x.", 6'd5, O[0][8][1]);
        end
        I[4][1][2] <= 6'd50;
        #1;
        if (!(O[4][1][2] === 6'd50)) begin
            $error("Failed on action=134 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][1][2].  Expected %x, got %x.", 6'd50, O[4][1][2]);
        end
        I[1][4][1] <= 6'd60;
        #1;
        if (!(O[1][4][1] === 6'd60)) begin
            $error("Failed on action=137 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][4][1].  Expected %x, got %x.", 6'd60, O[1][4][1]);
        end
        I[4][2][2] <= 6'd26;
        #1;
        if (!(O[4][2][2] === 6'd26)) begin
            $error("Failed on action=140 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][2][2].  Expected %x, got %x.", 6'd26, O[4][2][2]);
        end
        I[0][10][0] <= 6'd20;
        #1;
        if (!(O[0][10][0] === 6'd20)) begin
            $error("Failed on action=143 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][10][0].  Expected %x, got %x.", 6'd20, O[0][10][0]);
        end
        I[2][8][1] <= 6'd15;
        #1;
        if (!(O[2][8][1] === 6'd15)) begin
            $error("Failed on action=146 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][8][1].  Expected %x, got %x.", 6'd15, O[2][8][1]);
        end
        I[4][7][2] <= 6'd22;
        #1;
        if (!(O[4][7][2] === 6'd22)) begin
            $error("Failed on action=149 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][2].  Expected %x, got %x.", 6'd22, O[4][7][2]);
        end
        I[0][7][2] <= 6'd52;
        #1;
        if (!(O[0][7][2] === 6'd52)) begin
            $error("Failed on action=152 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][7][2].  Expected %x, got %x.", 6'd52, O[0][7][2]);
        end
        I[4][8][1] <= 6'd45;
        #1;
        if (!(O[4][8][1] === 6'd45)) begin
            $error("Failed on action=155 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][8][1].  Expected %x, got %x.", 6'd45, O[4][8][1]);
        end
        I[3][10][1] <= 6'd19;
        #1;
        if (!(O[3][10][1] === 6'd19)) begin
            $error("Failed on action=158 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][10][1].  Expected %x, got %x.", 6'd19, O[3][10][1]);
        end
        I[4][11][0] <= 6'd58;
        #1;
        if (!(O[4][11][0] === 6'd58)) begin
            $error("Failed on action=161 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][11][0].  Expected %x, got %x.", 6'd58, O[4][11][0]);
        end
        I[0][5][2] <= 6'd5;
        #1;
        if (!(O[0][5][2] === 6'd5)) begin
            $error("Failed on action=164 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][5][2].  Expected %x, got %x.", 6'd5, O[0][5][2]);
        end
        I[4][4][0] <= 6'd30;
        #1;
        if (!(O[4][4][0] === 6'd30)) begin
            $error("Failed on action=167 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][4][0].  Expected %x, got %x.", 6'd30, O[4][4][0]);
        end
        I[3][5][2] <= 6'd36;
        #1;
        if (!(O[3][5][2] === 6'd36)) begin
            $error("Failed on action=170 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][5][2].  Expected %x, got %x.", 6'd36, O[3][5][2]);
        end
        I[2][9][2] <= 6'd16;
        #1;
        if (!(O[2][9][2] === 6'd16)) begin
            $error("Failed on action=173 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][9][2].  Expected %x, got %x.", 6'd16, O[2][9][2]);
        end
        I[2][6][2] <= 6'd53;
        #1;
        if (!(O[2][6][2] === 6'd53)) begin
            $error("Failed on action=176 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][6][2].  Expected %x, got %x.", 6'd53, O[2][6][2]);
        end
        I[0][0][2] <= 6'd24;
        #1;
        if (!(O[0][0][2] === 6'd24)) begin
            $error("Failed on action=179 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][0][2].  Expected %x, got %x.", 6'd24, O[0][0][2]);
        end
        I[2][2][0] <= 6'd28;
        #1;
        if (!(O[2][2][0] === 6'd28)) begin
            $error("Failed on action=182 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][2][0].  Expected %x, got %x.", 6'd28, O[2][2][0]);
        end
        I[3][6][2] <= 6'd53;
        #1;
        if (!(O[3][6][2] === 6'd53)) begin
            $error("Failed on action=185 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][6][2].  Expected %x, got %x.", 6'd53, O[3][6][2]);
        end
        I[0][6][2] <= 6'd53;
        #1;
        if (!(O[0][6][2] === 6'd53)) begin
            $error("Failed on action=188 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][6][2].  Expected %x, got %x.", 6'd53, O[0][6][2]);
        end
        I[0][2][1] <= 6'd8;
        #1;
        if (!(O[0][2][1] === 6'd8)) begin
            $error("Failed on action=191 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][2][1].  Expected %x, got %x.", 6'd8, O[0][2][1]);
        end
        I[2][11][0] <= 6'd57;
        #1;
        if (!(O[2][11][0] === 6'd57)) begin
            $error("Failed on action=194 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][11][0].  Expected %x, got %x.", 6'd57, O[2][11][0]);
        end
        I[4][7][2] <= 6'd0;
        #1;
        if (!(O[4][7][2] === 6'd0)) begin
            $error("Failed on action=197 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][7][2].  Expected %x, got %x.", 6'd0, O[4][7][2]);
        end
        I[0][7][1] <= 6'd39;
        #1;
        if (!(O[0][7][1] === 6'd39)) begin
            $error("Failed on action=200 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][7][1].  Expected %x, got %x.", 6'd39, O[0][7][1]);
        end
        I[3][0][1] <= 6'd24;
        #1;
        if (!(O[3][0][1] === 6'd24)) begin
            $error("Failed on action=203 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][0][1].  Expected %x, got %x.", 6'd24, O[3][0][1]);
        end
        I[4][10][0] <= 6'd16;
        #1;
        if (!(O[4][10][0] === 6'd16)) begin
            $error("Failed on action=206 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][10][0].  Expected %x, got %x.", 6'd16, O[4][10][0]);
        end
        I[0][6][2] <= 6'd53;
        #1;
        if (!(O[0][6][2] === 6'd53)) begin
            $error("Failed on action=209 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][6][2].  Expected %x, got %x.", 6'd53, O[0][6][2]);
        end
        I[2][0][0] <= 6'd1;
        #1;
        if (!(O[2][0][0] === 6'd1)) begin
            $error("Failed on action=212 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][0][0].  Expected %x, got %x.", 6'd1, O[2][0][0]);
        end
        I[0][10][2] <= 6'd12;
        #1;
        if (!(O[0][10][2] === 6'd12)) begin
            $error("Failed on action=215 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][10][2].  Expected %x, got %x.", 6'd12, O[0][10][2]);
        end
        I[1][1][2] <= 6'd25;
        #1;
        if (!(O[1][1][2] === 6'd25)) begin
            $error("Failed on action=218 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][1][2].  Expected %x, got %x.", 6'd25, O[1][1][2]);
        end
        I[2][4][2] <= 6'd23;
        #1;
        if (!(O[2][4][2] === 6'd23)) begin
            $error("Failed on action=221 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][4][2].  Expected %x, got %x.", 6'd23, O[2][4][2]);
        end
        I[0][7][1] <= 6'd10;
        #1;
        if (!(O[0][7][1] === 6'd10)) begin
            $error("Failed on action=224 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][7][1].  Expected %x, got %x.", 6'd10, O[0][7][1]);
        end
        I[0][4][1] <= 6'd14;
        #1;
        if (!(O[0][4][1] === 6'd14)) begin
            $error("Failed on action=227 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][4][1].  Expected %x, got %x.", 6'd14, O[0][4][1]);
        end
        I[2][2][2] <= 6'd44;
        #1;
        if (!(O[2][2][2] === 6'd44)) begin
            $error("Failed on action=230 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][2][2].  Expected %x, got %x.", 6'd44, O[2][2][2]);
        end
        I[0][2][1] <= 6'd2;
        #1;
        if (!(O[0][2][1] === 6'd2)) begin
            $error("Failed on action=233 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][2][1].  Expected %x, got %x.", 6'd2, O[0][2][1]);
        end
        I[0][0][0] <= 6'd33;
        #1;
        if (!(O[0][0][0] === 6'd33)) begin
            $error("Failed on action=236 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][0][0].  Expected %x, got %x.", 6'd33, O[0][0][0]);
        end
        I[4][5][1] <= 6'd5;
        #1;
        if (!(O[4][5][1] === 6'd5)) begin
            $error("Failed on action=239 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][5][1].  Expected %x, got %x.", 6'd5, O[4][5][1]);
        end
        I[4][10][1] <= 6'd58;
        #1;
        if (!(O[4][10][1] === 6'd58)) begin
            $error("Failed on action=242 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[4][10][1].  Expected %x, got %x.", 6'd58, O[4][10][1]);
        end
        I[3][5][2] <= 6'd22;
        #1;
        if (!(O[3][5][2] === 6'd22)) begin
            $error("Failed on action=245 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][5][2].  Expected %x, got %x.", 6'd22, O[3][5][2]);
        end
        I[1][6][2] <= 6'd37;
        #1;
        if (!(O[1][6][2] === 6'd37)) begin
            $error("Failed on action=248 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][6][2].  Expected %x, got %x.", 6'd37, O[1][6][2]);
        end
        I[0][2][0] <= 6'd34;
        #1;
        if (!(O[0][2][0] === 6'd34)) begin
            $error("Failed on action=251 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][2][0].  Expected %x, got %x.", 6'd34, O[0][2][0]);
        end
        I[2][5][1] <= 6'd11;
        #1;
        if (!(O[2][5][1] === 6'd11)) begin
            $error("Failed on action=254 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][5][1].  Expected %x, got %x.", 6'd11, O[2][5][1]);
        end
        I[2][9][0] <= 6'd5;
        #1;
        if (!(O[2][9][0] === 6'd5)) begin
            $error("Failed on action=257 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][9][0].  Expected %x, got %x.", 6'd5, O[2][9][0]);
        end
        I[2][2][0] <= 6'd37;
        #1;
        if (!(O[2][2][0] === 6'd37)) begin
            $error("Failed on action=260 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][2][0].  Expected %x, got %x.", 6'd37, O[2][2][0]);
        end
        I[2][6][2] <= 6'd16;
        #1;
        if (!(O[2][6][2] === 6'd16)) begin
            $error("Failed on action=263 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][6][2].  Expected %x, got %x.", 6'd16, O[2][6][2]);
        end
        I[2][1][1] <= 6'd30;
        #1;
        if (!(O[2][1][1] === 6'd30)) begin
            $error("Failed on action=266 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][1][1].  Expected %x, got %x.", 6'd30, O[2][1][1]);
        end
        I[0][4][0] <= 6'd9;
        #1;
        if (!(O[0][4][0] === 6'd9)) begin
            $error("Failed on action=269 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][4][0].  Expected %x, got %x.", 6'd9, O[0][4][0]);
        end
        I[2][6][1] <= 6'd38;
        #1;
        if (!(O[2][6][1] === 6'd38)) begin
            $error("Failed on action=272 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[2][6][1].  Expected %x, got %x.", 6'd38, O[2][6][1]);
        end
        I[3][1][0] <= 6'd61;
        #1;
        if (!(O[3][1][0] === 6'd61)) begin
            $error("Failed on action=275 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][1][0].  Expected %x, got %x.", 6'd61, O[3][1][0]);
        end
        I[3][5][1] <= 6'd15;
        #1;
        if (!(O[3][5][1] === 6'd15)) begin
            $error("Failed on action=278 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][5][1].  Expected %x, got %x.", 6'd15, O[3][5][1]);
        end
        I[3][1][2] <= 6'd63;
        #1;
        if (!(O[3][1][2] === 6'd63)) begin
            $error("Failed on action=281 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][1][2].  Expected %x, got %x.", 6'd63, O[3][1][2]);
        end
        I[3][0][1] <= 6'd42;
        #1;
        if (!(O[3][0][1] === 6'd42)) begin
            $error("Failed on action=284 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][0][1].  Expected %x, got %x.", 6'd42, O[3][0][1]);
        end
        I[1][2][2] <= 6'd48;
        #1;
        if (!(O[1][2][2] === 6'd48)) begin
            $error("Failed on action=287 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][2][2].  Expected %x, got %x.", 6'd48, O[1][2][2]);
        end
        I[0][1][0] <= 6'd25;
        #1;
        if (!(O[0][1][0] === 6'd25)) begin
            $error("Failed on action=290 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][1][0].  Expected %x, got %x.", 6'd25, O[0][1][0]);
        end
        I[1][0][1] <= 6'd1;
        #1;
        if (!(O[1][0][1] === 6'd1)) begin
            $error("Failed on action=293 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[1][0][1].  Expected %x, got %x.", 6'd1, O[1][0][1]);
        end
        I[0][6][2] <= 6'd37;
        #1;
        if (!(O[0][6][2] === 6'd37)) begin
            $error("Failed on action=296 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[0][6][2].  Expected %x, got %x.", 6'd37, O[0][6][2]);
        end
        I[3][7][2] <= 6'd27;
        #1;
        if (!(O[3][7][2] === 6'd27)) begin
            $error("Failed on action=299 checking port test_system_verilog_target_packed_arrays_True__test_packed_arrays_stimulate_by_element.O[3][7][2].  Expected %x, got %x.", 6'd27, O[3][7][2]);
        end

        #20 $finish;
    end

endmodule
