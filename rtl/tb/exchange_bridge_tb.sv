`timescale 1ns/1ps

module exchange_bridge_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic intent_valid;
    logic side_buy = 1'b1;
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
    logic [63:0] max_net_position = 64'd1000;
    logic decision_valid;
    logic approved;
    logic [3:0] reason_code;
    logic [63:0] vectors [0:19];
    integer i;

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
        $readmemh("build/vectors/exchange_vectors.hex", vectors);
        intent_valid = 1'b0;
        trading_enabled = 1'b1;
        limits_valid = 1'b1;
        clock_healthy = 1'b1;
        feed_healthy = 1'b1;
        halted = 1'b0;
        net_position = 64'sd0;
        #2;
        rst_n = 1'b1;
        #8;
        for (i = 0; i < 4; i = i + 1) begin
            price_ticks = vectors[i * 5];
            quantity = vectors[i * 5 + 1];
            max_quantity = vectors[i * 5 + 2];
            max_notional_ticks = vectors[i * 5 + 3];
            intent_valid = 1'b1;
            @(posedge clk);
            #1 intent_valid = 1'b0;
            @(posedge clk);
            #1;
            if (!decision_valid) $fatal(1, "missing decision");
            if (approved !== vectors[i * 5 + 4][0]) $fatal(1, "vector mismatch");
        end
        $display("ito_exchange_bridge_pass");
        $finish;
    end
endmodule
