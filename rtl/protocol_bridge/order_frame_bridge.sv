module order_frame_bridge #(
    parameter integer WIDTH = 64
) (
    input logic clk,
    input logic rst_n,
    input logic frame_valid,
    input logic [WIDTH-1:0] frame_price_ticks,
    input logic [WIDTH-1:0] frame_quantity,
    input logic [WIDTH-1:0] frame_max_quantity,
    input logic [WIDTH-1:0] frame_max_notional_ticks,
    input logic signed [WIDTH-1:0] frame_net_position,
    input logic [WIDTH-1:0] frame_max_net_position,
    input logic [7:0] frame_control,
    input logic [7:0] frame_health,
    output logic risk_request_valid,
    output logic risk_side_buy,
    output logic risk_trading_enabled,
    output logic risk_halted,
    output logic risk_limits_valid,
    output logic risk_clock_healthy,
    output logic risk_feed_healthy,
    output logic [WIDTH-1:0] risk_price_ticks,
    output logic [WIDTH-1:0] risk_quantity,
    output logic [WIDTH-1:0] risk_max_quantity,
    output logic [WIDTH-1:0] risk_max_notional_ticks,
    output logic signed [WIDTH-1:0] risk_net_position,
    output logic [WIDTH-1:0] risk_max_net_position
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            risk_request_valid <= 1'b0;
            risk_side_buy <= 1'b0;
            risk_trading_enabled <= 1'b0;
            risk_halted <= 1'b1;
            risk_limits_valid <= 1'b0;
            risk_clock_healthy <= 1'b0;
            risk_feed_healthy <= 1'b0;
            risk_price_ticks <= '0;
            risk_quantity <= '0;
            risk_max_quantity <= '0;
            risk_max_notional_ticks <= '0;
            risk_net_position <= '0;
            risk_max_net_position <= '0;
        end else begin
            risk_request_valid <= frame_valid;
            if (frame_valid) begin
                risk_side_buy <= frame_control[2];
                risk_trading_enabled <= frame_control[0];
                risk_halted <= frame_control[1];
                risk_limits_valid <= frame_health[0];
                risk_clock_healthy <= frame_health[1];
                risk_feed_healthy <= frame_health[2];
                risk_price_ticks <= frame_price_ticks;
                risk_quantity <= frame_quantity;
                risk_max_quantity <= frame_max_quantity;
                risk_max_notional_ticks <= frame_max_notional_ticks;
                risk_net_position <= frame_net_position;
                risk_max_net_position <= frame_max_net_position;
            end
        end
    end
endmodule
