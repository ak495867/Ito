package ito_types;
    typedef enum logic [3:0] {
        REASON_NONE = 4'd0,
        REASON_DISABLED = 4'd1,
        REASON_LIMITS = 4'd2,
        REASON_HEALTH = 4'd3,
        REASON_QUANTITY = 4'd4,
        REASON_NOTIONAL = 4'd5,
        REASON_POSITION = 4'd6,
        REASON_PRICE_TICKS_ZERO = 4'd7
    } reason_t;
endpackage
