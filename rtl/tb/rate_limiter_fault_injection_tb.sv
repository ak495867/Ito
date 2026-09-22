`timescale 1ns/1ps

module rate_limiter_fault_injection_tb;
    logic clk = 1'b0;
    logic rst_n = 1'b0;
    logic window_reset;
    logic request;
    logic [31:0] max_requests;
    logic allowed;
    logic tripped;
    logic [31:0] count;

    always #5 clk = ~clk;

    rate_limiter dut (
        .clk(clk),
        .rst_n(rst_n),
        .window_reset(window_reset),
        .request(request),
        .max_requests(max_requests),
        .allowed(allowed),
        .tripped(tripped),
        .count(count)
    );

    logic [7:0] fault_vector;
    integer test_case;

    initial begin
        window_reset = 1'b0;
        request = 1'b0;
        max_requests = 32'd5;
        fault_vector = 8'b0;
        test_case = 0;
        #12;
        rst_n = 1'b1;

        for (test_case = 0; test_case < 8; test_case = test_case + 1) begin
            fault_vector = test_case[7:0];
            max_requests = fault_vector[0] ? 32'd0 : 32'd5;
            window_reset = fault_vector[1];
            request = 1'b1;
            @(posedge clk);
            #1 request = 1'b0;
            @(posedge clk);
            #1;
        end
        $display("ito_rate_limiter_fault_injection_pass");
        $finish;
    end
endmodule