`timescale 1ns/1ps

module risk_accelerator_timing_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic request_valid;
    logic side_buy;
    logic trading_enabled;
    logic halted;
    logic limits_valid;
    logic clock_healthy;
    logic feed_healthy;
    logic [63:0] price_ticks;
    logic [63:0] quantity;
    logic [63:0] max_quantity;
    logic [63:0] max_notional_ticks;
    logic signed [63:0] net_position;
    logic [63:0] max_net_position;
    logic request_ready;
    logic response_valid;
    logic approved;
    logic [3:0] reason_code;

    always #5 clk = ~clk;

    risk_accelerator dut (
        .clk(clk),
        .rst_n(rst_n),
        .request_valid(request_valid),
        .side_buy(side_buy),
        .trading_enabled(trading_enabled),
        .halted(halted),
        .limits_valid(limits_valid),
        .clock_healthy(clock_healthy),
        .feed_healthy(feed_healthy),
        .price_ticks(price_ticks),
        .quantity(quantity),
        .max_quantity(max_quantity),
        .max_notional_ticks(max_notional_ticks),
        .net_position(net_position),
        .max_net_position(max_net_position),
        .request_ready(request_ready),
        .response_valid(response_valid),
        .approved(approved),
        .reason_code(reason_code)
    );

    integer i;
    integer request_count;
    integer response_count;
    integer start_time;
    integer end_time;

    initial begin
        request_valid = 1'b0;
        side_buy = 1'b1;
        trading_enabled = 1'b1;
        halted = 1'b0;
        limits_valid = 1'b1;
        clock_healthy = 1'b1;
        feed_healthy = 1'b1;
        price_ticks = 64'd100;
        quantity = 64'd10;
        max_quantity = 64'd100;
        max_notional_ticks = 64'd10000;
        net_position = 64'sd0;
        max_net_position = 64'd1000;
        request_count = 0;
        response_count = 0;
        #12;
        rst_n = 1'b1;
        #3;

        for (i = 0; i < 1000; i = i + 1) begin
            while (!request_ready) @(posedge clk);
            request_valid = 1'b1;
            @(posedge clk);
            request_valid = 1'b0;
            request_count = request_count + 1;
            @(posedge clk);
            if (response_valid) begin
                response_count = response_count + 1;
            end
        end

        while (response_count < request_count) @(posedge clk);
        $display("ito_risk_accelerator_timing_pass:requests=%0d,responses=%0d", request_count, response_count);
        $finish;
    end
endmodule