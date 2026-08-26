package ito_types;
    typedef enum logic [2:0] {
        REASON_NONE = 3'd0,
        REASON_DISABLED = 3'd1,
        REASON_LIMITS = 3'd2,
        REASON_HEALTH = 3'd3,
        REASON_QUANTITY = 3'd4,
        REASON_NOTIONAL = 3'd5,
        REASON_POSITION = 3'd6
    } reason_t;
endpackage
