`timescale 1ns/1ps

module connectivity_control_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic request_valid;
    logic [15:0] preferred_venue;
    logic venue_a_ready;
    logic venue_b_ready;
    logic allow_failover;
    logic [15:0] selected_venue;
    logic selected_valid;
    logic failover_used;
    logic blocked;
    logic frame_valid;
    logic [63:0] frame_price_ticks;
    logic [63:0] frame_quantity;
    logic [63:0] frame_max_quantity;
    logic [63:0] frame_max_notional_ticks;
    logic signed [63:0] frame_net_position;
    logic [63:0] frame_max_net_position;
    logic [7:0] frame_control;
    logic [7:0] frame_health;
    logic risk_request_valid;
    logic risk_side_buy;
    logic risk_trading_enabled;
    logic risk_halted;
    logic risk_limits_valid;
    logic risk_clock_healthy;
    logic risk_feed_healthy;
    logic [63:0] risk_price_ticks;
    logic [63:0] risk_quantity;
    logic [63:0] risk_max_quantity;
    logic [63:0] risk_max_notional_ticks;
    logic signed [63:0] risk_net_position;
    logic [63:0] risk_max_net_position;
    logic request_ready;
    logic response_valid;
    logic approved;
    logic [3:0] reason_code;

    always #5 clk = ~clk;

    venue_mux mux (
        .request_valid(request_valid),
        .preferred_venue(preferred_venue),
        .venue_a_ready(venue_a_ready),
        .venue_b_ready(venue_b_ready),
        .allow_failover(allow_failover),
        .venue_a_id(16'd5),
        .venue_b_id(16'd6),
        .selected_valid(selected_valid),
        .selected_venue(selected_venue),
        .failover_used(failover_used),
        .blocked(blocked)
    );

    order_frame_bridge bridge (
        .clk(clk),
        .rst_n(rst_n),
        .frame_valid(frame_valid),
        .frame_price_ticks(frame_price_ticks),
        .frame_quantity(frame_quantity),
        .frame_max_quantity(frame_max_quantity),
        .frame_max_notional_ticks(frame_max_notional_ticks),
        .frame_net_position(frame_net_position),
        .frame_max_net_position(frame_max_net_position),
        .frame_control(frame_control),
        .frame_health(frame_health),
        .risk_request_valid(risk_request_valid),
        .risk_side_buy(risk_side_buy),
        .risk_trading_enabled(risk_trading_enabled),
        .risk_halted(risk_halted),
        .risk_limits_valid(risk_limits_valid),
        .risk_clock_healthy(risk_clock_healthy),
        .risk_feed_healthy(risk_feed_healthy),
        .risk_price_ticks(risk_price_ticks),
        .risk_quantity(risk_quantity),
        .risk_max_quantity(risk_max_quantity),
        .risk_max_notional_ticks(risk_max_notional_ticks),
        .risk_net_position(risk_net_position),
        .risk_max_net_position(risk_max_net_position)
    );

    risk_accelerator accelerator (
        .clk(clk),
        .rst_n(rst_n),
        .request_valid(risk_request_valid),
        .side_buy(risk_side_buy),
        .trading_enabled(risk_trading_enabled),
        .halted(risk_halted),
        .limits_valid(risk_limits_valid),
        .clock_healthy(risk_clock_healthy),
        .feed_healthy(risk_feed_healthy),
        .price_ticks(risk_price_ticks),
        .quantity(risk_quantity),
        .max_quantity(risk_max_quantity),
        .max_notional_ticks(risk_max_notional_ticks),
        .net_position(risk_net_position),
        .max_net_position(risk_max_net_position),
        .request_ready(request_ready),
        .response_valid(response_valid),
        .approved(approved),
        .reason_code(reason_code)
    );

    initial begin
        request_valid = 1'b1;
        preferred_venue = 16'd5;
        venue_a_ready = 1'b0;
        venue_b_ready = 1'b1;
        allow_failover = 1'b1;
        frame_valid = 1'b0;
        frame_price_ticks = 64'd100;
        frame_quantity = 64'd10;
        frame_max_quantity = 64'd100;
        frame_max_notional_ticks = 64'd10000;
        frame_net_position = 64'sd0;
        frame_max_net_position = 64'd1000;
        frame_control = 8'b00000101;
        frame_health = 8'b00000111;
        #1;
        if (!selected_valid || selected_venue != 16'd6 || !failover_used || blocked) $fatal(1, "venue failover mismatch");
        request_valid = 1'b0;
        #11;
        rst_n = 1'b1;
        #2;
        frame_valid = 1'b1;
        @(posedge clk);
        #1 frame_valid = 1'b0;
        @(posedge clk);
        @(posedge clk);
        #1;
        if (!response_valid || !approved || reason_code != 4'd0) $fatal(1, "protocol hardware pipeline mismatch");
        $display("ito_connectivity_control_pass");
        $finish;
    end
endmodule
