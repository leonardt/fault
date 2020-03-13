module clkdelay #(
    parameter integer n_cyc=`N_CYC,
    parameter integer n_bits=`N_BITS
) (
    input wire logic clk,
    input wire logic rst,
    output reg [n_bits-1:0] count,
    output reg n_done
);

    always @(posedge clk) begin
        if (rst == 1'b1) begin
            count <= 0;
            n_done <= 1;
        end else if (count >= n_cyc-1) begin
            count <= count;
            n_done <= 0;
        end else begin
            count <= count + 1;
            n_done <= 1;
        end
    end

endmodule
