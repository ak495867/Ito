module pre_trade_gate #(
    parameter integer WIDTH = 64
) (
    input logic clk,
    input logic rst_n,
    input logic intent_valid,
    input logic side_buy,
    input logic trading_enabled,
    input logic limits_valid,
    input logic clock_healthy,
    input logic feed_healthy,
    input logic halted,
    input logic [WIDTH-1:0] price_ticks,
    input logic [WIDTH-1:0] quantity,
    input logic [WIDTH-1:0] max_quantity,
    input logic [WIDTH-1:0] max_notional_ticks,
    input logic signed [WIDTH-1:0] net_position,
    input logic [WIDTH-1:0] max_net_position,
    output logic decision_valid,
    output logic approved,
    output logic [3:0] reason_code
);
    logic stage_valid;
    logic stage_side_buy;
    logic stage_trading_enabled;
    logic stage_limits_valid;
    logic stage_clock_healthy;
    logic stage_feed_healthy;
    logic stage_halted;
    logic [WIDTH-1:0] stage_price_ticks;
    logic [WIDTH-1:0] stage_quantity;
    logic [WIDTH-1:0] stage_max_quantity;
    logic [WIDTH-1:0] stage_max_notional_ticks;
    logic signed [WIDTH-1:0] stage_net_position;
    logic [WIDTH-1:0] stage_max_net_position;
    logic [2*WIDTH-1:0] notional;
    logic signed [WIDTH:0] signed_quantity;
    logic signed [WIDTH:0] next_position;
    logic decision_comb;
    logic [3:0] reason_comb;

    always_comb begin
        notional = stage_price_ticks * stage_quantity;
        signed_quantity = stage_side_buy ? $signed({1'b0, stage_quantity}) : -$signed({1'b0, stage_quantity});
        next_position = $signed({stage_net_position[WIDTH-1], stage_net_position}) + signed_quantity;
        decision_comb = 1'b0;
        reason_comb = 4'd0;
        if (!stage_trading_enabled || stage_halted) begin
            reason_comb = 4'd1;
        end else if (!stage_limits_valid) begin
            reason_comb = 4'd2;
        end else if (!stage_clock_healthy || !stage_feed_healthy) begin
            reason_comb = 4'd3;
        end else if (stage_quantity == 0 || stage_quantity > stage_max_quantity) begin
            reason_comb = 4'd4;
        end else if (stage_price_ticks == 0) begin
            reason_comb = 4'd5;
        end else if (notional > stage_max_notional_ticks) begin
            reason_comb = 4'd6;
        end else if (next_position > $signed({1'b0, stage_max_net_position}) || next_position < -$signed({1'b0, stage_max_net_position})) begin
            reason_comb = 4'd7;
        end else begin
            decision_comb = 1'b1;
        end
    end

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage_valid <= 1'b0;
            decision_valid <= 1'b0;
            approved <= 1'b0;
            reason_code <= 4'd1;
        end else begin
            decision_valid <= stage_valid;
            if (stage_valid) begin
                approved <= decision_comb;
                reason_code <= reason_comb;
            end
            stage_valid <= intent_valid;
            if (intent_valid) begin
                stage_side_buy <= side_buy;
                stage_trading_enabled <= trading_enabled;
                stage_limits_valid <= limits_valid;
                stage_clock_healthy <= clock_healthy;
                stage_feed_healthy <= feed_healthy;
                stage_halted <= halted;
                stage_price_ticks <= price_ticks;
                stage_quantity <= quantity;
                stage_max_quantity <= max_quantity;
                stage_max_notional_ticks <= max_notional_ticks;
                stage_net_position <= net_position;
                stage_max_net_position <= max_net_position;
            end
        end
    end
endmodule
