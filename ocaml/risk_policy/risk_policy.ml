type decision = Approved | TradingDisabled | QuantityLimit | PriceLimit | NotionalLimit | PositionLimit | RateLimit | HealthFailure

type side = Buy | Sell

type limits = {
  trading_enabled : bool;
  max_order_quantity : int64;
  max_order_notional : int64;
  max_net_position : int64;
  max_orders_per_second : int64;
}

type order = {
  price_ticks : int64;
  quantity : int64;
  side : side;
  net_position : int64;
  orders_per_second : int64;
  healthy : bool;
}

let validate limits request =
  if not limits.trading_enabled then TradingDisabled
  else if not request.healthy then HealthFailure
  else if request.quantity <= 0L || request.quantity > limits.max_order_quantity then QuantityLimit
  else if request.price_ticks <= 0L then PriceLimit
  else if limits.max_order_notional <= 0L || request.price_ticks > Int64.div limits.max_order_notional request.quantity then NotionalLimit
  else
    let position_valid = match request.side with
      | Buy -> Int64.compare request.net_position (Int64.sub limits.max_net_position request.quantity) <= 0
      | Sell -> Int64.compare request.net_position (Int64.add (Int64.neg limits.max_net_position) request.quantity) >= 0 in
    if not position_valid then PositionLimit
    else if request.orders_per_second < 0L || request.orders_per_second > limits.max_orders_per_second then RateLimit
    else Approved

let decision_name = function
  | Approved -> "approved"
  | TradingDisabled -> "trading_disabled"
  | QuantityLimit -> "quantity_limit"
  | PriceLimit -> "price_limit"
  | NotionalLimit -> "notional_limit"
  | PositionLimit -> "position_limit"
  | RateLimit -> "rate_limit"
  | HealthFailure -> "health_failure"

let default_limits = { trading_enabled = false; max_order_quantity = 100L; max_order_notional = 1_000_000L; max_net_position = 1_000L; max_orders_per_second = 10L }

let () =
  let request = { price_ticks = 100L; quantity = 10L; side = Buy; net_position = 0L; orders_per_second = 1L; healthy = true } in
  print_endline (decision_name (validate default_limits request));
  ignore (validate { default_limits with max_net_position = 10L } { request with side = Sell; net_position = -10L })
