`timescale 1ns/1ps

module rate_limiter_tb;
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

    initial begin
        window_reset = 1'b0;
        request = 1'b0;
        max_requests = 32'd2;
        #12;
        rst_n = 1'b1;
        request = 1'b1;
        @(posedge clk);
        #1 if (!allowed || count != 1) $fatal(1, "rate limit first request failed");
        @(posedge clk);
        #1 if (!allowed || count != 2) $fatal(1, "rate limit second request failed");
        @(posedge clk);
        #1 if (allowed || !tripped) $fatal(1, "rate limit trip failed");
        request = 1'b0;
        window_reset = 1'b1;
        @(posedge clk);
        #1 if (tripped || count != 0) $fatal(1, "rate limit reset failed");
        $display("ito_rate_limiter_pass");
        $finish;
    end
endmodule
