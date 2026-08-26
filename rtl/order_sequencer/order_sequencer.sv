module order_sequencer #(
    parameter integer WIDTH = 64
) (
    input logic clk,
    input logic rst_n,
    input logic halt,
    input logic approved_valid,
    input logic tx_ready,
    input logic [WIDTH-1:0] client_order_id,
    input logic [WIDTH-1:0] price_ticks,
    input logic [WIDTH-1:0] quantity,
    output logic tx_valid,
    output logic [WIDTH-1:0] tx_order_id,
    output logic [WIDTH-1:0] tx_price_ticks,
    output logic [WIDTH-1:0] tx_quantity,
    output logic busy
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_valid <= 1'b0;
            tx_order_id <= '0;
            tx_price_ticks <= '0;
            tx_quantity <= '0;
            busy <= 1'b0;
        end else if (halt) begin
            tx_valid <= 1'b0;
            busy <= 1'b0;
        end else begin
            if (!busy && approved_valid) begin
                tx_order_id <= client_order_id;
                tx_price_ticks <= price_ticks;
                tx_quantity <= quantity;
                tx_valid <= 1'b1;
                busy <= 1'b1;
            end else if (busy && tx_ready) begin
                tx_valid <= 1'b0;
                busy <= 1'b0;
            end
        end
    end
endmodule
