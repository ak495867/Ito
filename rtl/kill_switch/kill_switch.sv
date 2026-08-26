module kill_switch (
    input logic clk,
    input logic rst_n,
    input logic local_halt,
    input logic remote_halt,
    input logic watchdog_halt,
    input logic clear_request,
    output logic halted,
    output logic cancel_all
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            halted <= 1'b1;
            cancel_all <= 1'b1;
        end else if (local_halt || remote_halt || watchdog_halt) begin
            halted <= 1'b1;
            cancel_all <= 1'b1;
        end else if (clear_request) begin
            halted <= 1'b0;
            cancel_all <= 1'b0;
        end
    end
endmodule
