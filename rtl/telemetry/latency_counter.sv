module latency_counter #(
    parameter integer WIDTH = 32
) (
    input logic clk,
    input logic rst_n,
    input logic start,
    input logic stop,
    output logic active,
    output logic valid,
    output logic [WIDTH-1:0] cycles
);
    logic [WIDTH-1:0] counter;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0;
            valid <= 1'b0;
            cycles <= '0;
            counter <= '0;
        end else begin
            valid <= 1'b0;
            if (start && !active) begin
                active <= 1'b1;
                counter <= '0;
            end else if (active) begin
                if (stop) begin
                    active <= 1'b0;
                    valid <= 1'b1;
                    cycles <= counter;
                end else begin
                    counter <= counter + 1'b1;
                end
            end
        end
    end
endmodule
