open Yojson.Safe.Util

let ( >>= ) = Result.bind

let required_string object_value key =
  match object_value |> member key |> to_string_option with
  | Some value when String.length value > 0 -> Ok value
  | _ -> Error (key ^ "_missing")

let required_int object_value key =
  try
    let value = object_value |> member key |> to_int |> Int64.of_int in
    if value > 0L then Ok value else Error (key ^ "_invalid")
  with Type_error _ -> Error (key ^ "_missing")

let validate_breaker breaker =
  required_string breaker "id" >>= fun _ ->
  required_string breaker "scope" >>= fun _ ->
  required_string breaker "trigger" >>= fun _ ->
  required_int breaker "threshold" >>= fun _ ->
  required_string breaker "action" >>= fun _ ->
  required_string breaker "recovery"

let validate_risk_policy value now_ns =
  required_int value "policy_version" >>= fun _ ->
  required_int value "expires_at_ns" >>= fun expires_at_ns ->
  if expires_at_ns <= now_ns then Error "policy_expired" else
  let pre_trade = value |> member "pre_trade" in
  required_int pre_trade "max_order_quantity" >>= fun _ ->
  required_int pre_trade "max_order_notional_ticks" >>= fun _ ->
  required_int pre_trade "max_net_position" >>= fun _ ->
  required_int pre_trade "max_orders_per_second" >>= fun _ ->
  Ok ()

let validate_circuit_breaker_policy value now_ns =
  required_int value "policy_version" >>= fun _ ->
  required_int value "expires_at_ns" >>= fun expires_at_ns ->
  if expires_at_ns <= now_ns then Error "policy_expired" else
  let circuit_breakers = value |> member "breakers" |> to_list in
  match List.find_opt (fun breaker -> validate_breaker breaker |> Result.is_error) circuit_breakers with
  | Some breaker -> validate_breaker breaker |> Result.get_error |> fun reason -> Error reason
  | None -> Ok ()

let read_json path =
  Yojson.Safe.from_file path

let main risk_path breaker_path =
  try
    let risk_policy = read_json risk_path in
    let breaker_policy = read_json breaker_path in
    let now_ns = Int64.of_float (Unix.gettimeofday () *. 1_000_000_000.) in
    match validate_risk_policy risk_policy now_ns, validate_circuit_breaker_policy breaker_policy now_ns with
    | Ok (), Ok () -> print_endline "policy_valid"
    | Error reason, _ -> print_endline ("policy_invalid:" ^ reason)
    | _, Error reason -> print_endline ("circuit_breaker_invalid:" ^ reason)
  with
  | Sys_error reason -> print_endline ("file_error:" ^ reason)
  | Yojson.Json_error reason -> print_endline ("json_error:" ^ reason)
  | Type_error (reason, _) -> print_endline ("type_error:" ^ reason)

let () =
  let risk_path = if Array.length Sys.argv > 1 then Sys.argv.(1) else "config/risk/default_risk_policy.json" in
  let breaker_path = if Array.length Sys.argv > 2 then Sys.argv.(2) else "config/circuit_breakers/default_circuit_breakers.json" in
  main risk_path breaker_path
