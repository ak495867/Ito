package ito_risk_frame_pkg;
localparam integer REGISTER_MAP_VERSION = 2;
localparam integer FRAME_BYTES = 64;
localparam integer FRAME_BITS = 512;
localparam integer OFFSET_PRICE_TICKS = 0;
localparam integer OFFSET_QUANTITY = 8;
localparam integer OFFSET_MAX_QUANTITY = 16;
localparam integer OFFSET_MAX_NOTIONAL_TICKS = 24;
localparam integer OFFSET_NET_POSITION = 32;
localparam integer OFFSET_MAX_NET_POSITION = 40;
localparam integer OFFSET_CONTROL = 48;
localparam integer OFFSET_HEALTH = 49;
localparam integer OFFSET_LIMITS_VERSION = 56;
endpackage
