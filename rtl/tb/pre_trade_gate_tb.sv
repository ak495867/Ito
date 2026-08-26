`timescale 1ns/1ps

module pre_trade_gate_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic intent_valid;
    logic side_buy;
    logic trading_enabled;
    logic limits_valid;
    logic clock_healthy;
    logic feed_healthy;
    logic halted;
    logic [63:0] price_ticks;
    logic [63:0] quantity;
    logic [63:0] max_quantity;
    logic [63:0] max_notional_ticks;
    logic signed [63:0] net_position;
    logic [63:0] max_net_position;
    logic decision_valid;
    logic approved;
    logic [3:0] reason_code;

    always #5 clk = ~clk;

    pre_trade_gate dut (
        .clk(clk),
        .rst_n(rst_n),
        .intent_valid(intent_valid),
        .side_buy(side_buy),
        .trading_enabled(trading_enabled),
        .limits_valid(limits_valid),
        .clock_healthy(clock_healthy),
        .feed_healthy(feed_healthy),
        .halted(halted),
        .price_ticks(price_ticks),
        .quantity(quantity),
        .max_quantity(max_quantity),
        .max_notional_ticks(max_notional_ticks),
        .net_position(net_position),
        .max_net_position(max_net_position),
        .decision_valid(decision_valid),
        .approved(approved),
        .reason_code(reason_code)
    );

    initial begin
        intent_valid = 1'b0;
        side_buy = 1'b1;
        trading_enabled = 1'b1;
        limits_valid = 1'b1;
        clock_healthy = 1'b1;
        feed_healthy = 1'b1;
        halted = 1'b0;
        price_ticks = 64'd100;
        quantity = 64'd10;
        max_quantity = 64'd100;
        max_notional_ticks = 64'd10000;
        net_position = 64'sd0;
        max_net_position = 64'd1000;
        #2;
        rst_n = 1'b1;
        #10;
        intent_valid = 1'b1;
        @(posedge clk);
        #1 intent_valid = 1'b0;
        @(posedge clk);
        #1 if (!decision_valid || !approved) $fatal(1, "approved order was not accepted");
        quantity = 64'd101;
        intent_valid = 1'b1;
        @(posedge clk);
        #1 intent_valid = 1'b0;
        @(posedge clk);
        #1 if (!decision_valid || approved || reason_code != 4'd4) $fatal(1, "quantity limit was not enforced");
        quantity = 64'd10;
        clock_healthy = 1'b0;
        intent_valid = 1'b1;
        @(posedge clk);
        #1 intent_valid = 1'b0;
        @(posedge clk);
        #1 if (!decision_valid || approved || reason_code != 4'd3) $fatal(1, "clock health was not enforced");
        clock_healthy = 1'b1;
        side_buy = 1'b0;
        net_position = -64'sd1000;
        quantity = 64'd1;
        intent_valid = 1'b1;
        @(posedge clk);
        #1 intent_valid = 1'b0;
        @(posedge clk);
        #1 if (!decision_valid || approved || reason_code != 4'd7) $fatal(1, "sell lower bound was not enforced");
        $display("ito_pre_trade_gate_pass");
        $finish;
    end
endmodule
