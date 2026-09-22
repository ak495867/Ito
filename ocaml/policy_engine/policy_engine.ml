open Yojson.Safe.Util

let ( >>= ) = Result.bind

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

let required_string object_value key =
  match object_value |> member key |> to_string_option with
  | Some value when String.length value > 0 -> Ok value
  | _ -> Error (key ^ "_missing")

let required_int object_value key =
  try
    let value = object_value |> member key |> to_int |> Int64.of_int in
    if value > 0L then Ok value else Error (key ^ "_invalid")
  with Type_error _ -> Error (key ^ "_missing")

let required_bool object_value key =
  match object_value |> member key |> to_bool_option with
  | Some value -> Ok value
  | None -> Error (key ^ "_missing")

let validate_limits_json value =
  required_int value "max_quantity" >>= fun max_quantity ->
  required_int value "max_notional" >>= fun max_notional ->
  required_int value "max_position" >>= fun max_position ->
  required_int value "expires_at_ns" >>= fun expires_at_ns ->
  required_bool value "trading_enabled" >>= fun trading_enabled ->
  Ok { max_quantity; max_notional; max_position; expires_at_ns; trading_enabled }

let validate_policy_version value now_ns =
  required_int value "policy_version" >>= fun version ->
  required_int value "expires_at_ns" >>= fun expires_at_ns ->
  if expires_at_ns <= now_ns then Error "policy_expired" else
  if version <= 0L then Error "policy_version_invalid" else
  Ok version

let validate_monotonicity previous current =
  if Int64.compare current previous <= 0 then Error "policy_version_not_monotonic" else Ok ()

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

let validate_policy_file path now_ns =
  match Yojson.Safe.from_file path with
  | value -> validate_policy_version value now_ns
  | exception Yojson.Json_error reason -> Error ("json_error:" ^ reason)
  | exception Sys_error reason -> Error ("file_error:" ^ reason)

let () =
  let limits = { max_quantity = 100L; max_notional = 1_000_000L; max_position = 1_000L; expires_at_ns = 10_000L; trading_enabled = true } in
  let mode = List.hd all_modes in
  let verdict = validate mode limits 2_000L Buy 10L 100L 0L in
  print_endline (string_of_verdict verdict);
  ignore (validate mode limits 2_000L Sell 10L 100L 0L)