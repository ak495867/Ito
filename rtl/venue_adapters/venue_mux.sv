module venue_mux #(
    parameter integer VENUE_WIDTH = 16
) (
    input logic request_valid,
    input logic [VENUE_WIDTH-1:0] preferred_venue,
    input logic venue_a_ready,
    input logic venue_b_ready,
    input logic allow_failover,
    input logic [VENUE_WIDTH-1:0] venue_a_id,
    input logic [VENUE_WIDTH-1:0] venue_b_id,
    output logic selected_valid,
    output logic [VENUE_WIDTH-1:0] selected_venue,
    output logic failover_used,
    output logic blocked
);
    always_comb begin
        selected_valid = 1'b0;
        selected_venue = '0;
        failover_used = 1'b0;
        blocked = 1'b0;
        if (request_valid) begin
            if (preferred_venue == venue_a_id && venue_a_ready) begin
                selected_valid = 1'b1;
                selected_venue = venue_a_id;
            end else if (preferred_venue == venue_b_id && venue_b_ready) begin
                selected_valid = 1'b1;
                selected_venue = venue_b_id;
            end else if (allow_failover && venue_a_ready) begin
                selected_valid = 1'b1;
                selected_venue = venue_a_id;
                failover_used = 1'b1;
            end else if (allow_failover && venue_b_ready) begin
                selected_valid = 1'b1;
                selected_venue = venue_b_id;
                failover_used = 1'b1;
            end else begin
                blocked = 1'b1;
            end
        end
    end
endmodule
