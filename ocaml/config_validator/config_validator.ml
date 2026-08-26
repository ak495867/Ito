type config = {
  branch_id : string;
  entity_id : string;
  policy_version : int;
  expires_at_ns : int64;
  trading_enabled : bool;
}

type validation = Valid | Invalid of string

let validate config now_ns =
  if String.length config.branch_id = 0 then Invalid "branch_id_missing"
  else if String.length config.entity_id = 0 then Invalid "entity_id_missing"
  else if config.policy_version <= 0 then Invalid "policy_version_invalid"
  else if config.expires_at_ns <= now_ns then Invalid "policy_expired"
  else if not config.trading_enabled then Invalid "trading_disabled"
  else Valid

let () =
  let config = { branch_id = "branch-ny"; entity_id = "entity-alpha"; policy_version = 1; expires_at_ns = 10_000L; trading_enabled = true } in
  match validate config 1_000L with
  | Valid -> print_endline "valid"
  | Invalid reason -> print_endline ("invalid:" ^ reason)
