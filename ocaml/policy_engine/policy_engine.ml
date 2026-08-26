type branch_mode = Normal | Degraded | Restricted | Halted
type side = Buy | Sell

type limits = {
  max_quantity : int64;
  max_notional : int64;
  max_position : int64;
  expires_at_ns : int64;
  trading_enabled : bool;
}

type verdict = Approved | Rejected of string

let all_modes = [Normal; Degraded; Restricted; Halted]

let validate mode limits now_ns side quantity price position =
  match mode with
  | Halted -> Rejected "branch_halted"
  | Restricted -> Rejected "branch_restricted"
  | Degraded when limits.expires_at_ns <= now_ns -> Rejected "policy_expired"
  | _ when not limits.trading_enabled -> Rejected "trading_disabled"
  | _ when quantity <= 0L || quantity > limits.max_quantity -> Rejected "quantity_limit"
  | _ when price <= 0L -> Rejected "price_invalid"
  | _ when limits.max_notional <= 0L || price > Int64.div limits.max_notional quantity -> Rejected "notional_limit"
  | _ when (match side with Buy -> Int64.compare position (Int64.sub limits.max_position quantity) > 0 | Sell -> Int64.compare position (Int64.add (Int64.neg limits.max_position) quantity) < 0) -> Rejected "position_limit"
  | _ -> Approved

let string_of_verdict = function
  | Approved -> "approved"
  | Rejected reason -> "rejected:" ^ reason

let () =
  let limits = { max_quantity = 100L; max_notional = 1_000_000L; max_position = 1_000L; expires_at_ns = 10_000L; trading_enabled = true } in
  let mode = List.hd all_modes in
  let verdict = validate mode limits 2_000L Buy 10L 100L 0L in
  print_endline (string_of_verdict verdict);
  ignore (validate mode limits 2_000L Sell 10L 100L 0L)
