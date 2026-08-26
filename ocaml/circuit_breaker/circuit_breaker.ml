type scope = Strategy | Venue | Branch | Group

type state = Closed | Open | HalfOpen

type rule = {
  identifier : string;
  scope : scope;
  threshold : int64;
  cooldown_ns : int64;
  manual_clear : bool;
}

type breaker = {
  rule : rule;
  state : state;
  observed : int64;
  opened_at_ns : int64;
}

let trip breaker now_ns =
  if breaker.state = Closed && breaker.observed >= breaker.rule.threshold then { breaker with state = Open; opened_at_ns = now_ns }
  else breaker

let ready_for_probe breaker now_ns =
  breaker.state = Open && not breaker.rule.manual_clear && now_ns >= Int64.add breaker.opened_at_ns breaker.rule.cooldown_ns

let clear breaker =
  if breaker.rule.manual_clear then { breaker with state = Closed; observed = 0L; opened_at_ns = 0L }
  else breaker

let state_name = function
  | Closed -> "closed"
  | Open -> "open"
  | HalfOpen -> "half_open"

let sample_rule = { identifier = "CB-RISK-001"; scope = Strategy; threshold = 250_000L; cooldown_ns = 30_000_000_000L; manual_clear = true }

let () =
  let breaker = { rule = sample_rule; state = Closed; observed = 250_000L; opened_at_ns = 0L } in
  print_endline (state_name (trip breaker 1L).state)
