import ito_risk_frame_pkg::*;

module risk_accelerator #(
    parameter integer WIDTH = 64
) (
    input logic clk,
    input logic rst_n,
    input logic request_valid,
    input logic side_buy,
    input logic trading_enabled,
    input logic halted,
    input logic limits_valid,
    input logic clock_healthy,
    input logic feed_healthy,
    input logic [WIDTH-1:0] price_ticks,
    input logic [WIDTH-1:0] quantity,
    input logic [WIDTH-1:0] max_quantity,
    input logic [WIDTH-1:0] max_notional_ticks,
    input logic signed [WIDTH-1:0] net_position,
    input logic [WIDTH-1:0] max_net_position,
    output logic request_ready,
    output logic response_valid,
    output logic approved,
    output logic [3:0] reason_code
);
    logic stage1_valid;
    logic stage1_side_buy;
    logic stage1_trading_enabled;
    logic stage1_halted;
    logic stage1_limits_valid;
    logic stage1_clock_healthy;
    logic stage1_feed_healthy;
    logic [WIDTH-1:0] stage1_price_ticks;
    logic [WIDTH-1:0] stage1_quantity;
    logic [WIDTH-1:0] stage1_max_quantity;
    logic [WIDTH-1:0] stage1_max_notional_ticks;
    logic signed [WIDTH-1:0] stage1_net_position;
    logic [WIDTH-1:0] stage1_max_net_position;
    logic [2*WIDTH-1:0] notional;
    logic signed [WIDTH:0] signed_quantity;
    logic signed [WIDTH:0] next_position;
    logic decision_comb;
    logic [3:0] reason_comb;

    assign request_ready = !stage1_valid || response_valid;

    always_comb begin
        notional = stage1_price_ticks * stage1_quantity;
        signed_quantity = stage1_side_buy ? $signed({1'b0, stage1_quantity}) : -$signed({1'b0, stage1_quantity});
        next_position = $signed({stage1_net_position[WIDTH-1], stage1_net_position}) + signed_quantity;
        decision_comb = 1'b0;
        reason_comb = 4'd0;
        if (!stage1_trading_enabled || stage1_halted) begin
            reason_comb = 4'd1;
        end else if (!stage1_limits_valid) begin
            reason_comb = 4'd2;
        end else if (!stage1_clock_healthy || !stage1_feed_healthy) begin
            reason_comb = 4'd3;
        end else if (stage1_quantity == 0 || stage1_quantity > stage1_max_quantity) begin
            reason_comb = 4'd4;
        end else if (stage1_price_ticks == 0) begin
            reason_comb = 4'd5;
        end else if (notional > stage1_max_notional_ticks) begin
            reason_comb = 4'd6;
        end else if (next_position > $signed({1'b0, stage1_max_net_position}) || next_position < -$signed({1'b0, stage1_max_net_position})) begin
            reason_comb = 4'd7;
        end else begin
            decision_comb = 1'b1;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_valid <= 1'b0;
            response_valid <= 1'b0;
            approved <= 1'b0;
            reason_code <= 4'd1;
        end else begin
            response_valid <= stage1_valid;
            if (stage1_valid) begin
                approved <= decision_comb;
                reason_code <= reason_comb;
            end
            stage1_valid <= request_valid;
            if (request_valid) begin
                stage1_side_buy <= side_buy;
                stage1_trading_enabled <= trading_enabled;
                stage1_halted <= halted;
                stage1_limits_valid <= limits_valid;
                stage1_clock_healthy <= clock_healthy;
                stage1_feed_healthy <= feed_healthy;
                stage1_price_ticks <= price_ticks;
                stage1_quantity <= quantity;
                stage1_max_quantity <= max_quantity;
                stage1_max_notional_ticks <= max_notional_ticks;
                stage1_net_position <= net_position;
                stage1_max_net_position <= max_net_position;
            end
        end
    end
endmodule
