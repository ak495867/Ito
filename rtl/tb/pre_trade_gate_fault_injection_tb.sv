`timescale 1ns/1ps

module pre_trade_gate_fault_injection_tb;
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

    logic [7:0] fault_vector;
    integer test_case;

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
        fault_vector = 8'b0;
        test_case = 0;
        #2;
        rst_n = 1'b1;
        #10;

        for (test_case = 0; test_case < 16; test_case = test_case + 1) begin
            fault_vector = test_case[7:0];
            clock_healthy = ~fault_vector[0];
            feed_healthy = ~fault_vector[1];
            halted = fault_vector[2];
            limits_valid = ~fault_vector[3];
            trading_enabled = ~fault_vector[4];
            price_ticks = fault_vector[5] ? 64'd0 : 64'd100;
            quantity = fault_vector[6] ? 64'd200 : 64'd10;
            side_buy = fault_vector[7] ? 1'b0 : 1'b1;

            intent_valid = 1'b1;
            @(posedge clk);
            #1 intent_valid = 1'b0;
            @(posedge clk);
            #1;

            if (!decision_valid) $fatal(1, "Fault case %0d: missing decision", test_case);
        end
        $display("ito_pre_trade_gate_fault_injection_pass");
        $finish;
    end
endmodule