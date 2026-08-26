module rate_limiter #(
    parameter integer WIDTH = 32
) (
    input logic clk,
    input logic rst_n,
    input logic window_reset,
    input logic request,
    input logic [WIDTH-1:0] max_requests,
    output logic allowed,
    output logic tripped,
    output logic [WIDTH-1:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= '0;
            allowed <= 1'b0;
            tripped <= 1'b0;
        end else if (window_reset) begin
            count <= '0;
            allowed <= 1'b0;
            tripped <= 1'b0;
        end else begin
            allowed <= 1'b0;
            if (request) begin
                if (count < max_requests) begin
                    count <= count + 1'b1;
                    allowed <= 1'b1;
                end else begin
                    tripped <= 1'b1;
                end
            end
        end
    end
endmodule
