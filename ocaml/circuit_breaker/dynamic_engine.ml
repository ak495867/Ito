module RuleMap = Map.Make(String)

type scope = Strategy | Venue | Branch | Group

type state = Closed | Open | HalfOpen

type rule = { identifier : string; scope : scope; threshold : int64; cooldown_ns : int64; manual_clear : bool }
type runtime = { rule : rule; state : state; violations : int64; opened_at_ns : int64; trips : int64 }
type policy_update = Add of rule | Replace of rule | Remove of string

let empty = RuleMap.empty

let saturating_add left right =
  if Int64.compare right 0L > 0 && Int64.compare left (Int64.sub Int64.max_int right) > 0 then Int64.max_int
  else if Int64.compare right 0L < 0 && Int64.compare left (Int64.sub Int64.min_int right) < 0 then Int64.min_int
  else Int64.add left right

let install engine rule =
  if rule.identifier = "" || rule.threshold <= 0L || rule.cooldown_ns < 0L then engine
  else RuleMap.add rule.identifier { rule; state = Closed; violations = 0L; opened_at_ns = 0L; trips = 0L } engine

let apply_update engine = function
  | Add rule -> install engine rule
  | Replace rule -> install engine rule
  | Remove identifier -> RuleMap.remove identifier engine

let state engine identifier =
  match RuleMap.find_opt identifier engine with
  | Some runtime -> Some runtime.state
  | None -> None

let observe engine identifier amount now_ns =
  match RuleMap.find_opt identifier engine with
  | None -> engine
  | Some runtime ->
      if runtime.state = Open || amount <= 0L then engine
      else
        let violations = saturating_add runtime.violations amount in
        if violations >= runtime.rule.threshold then
          RuleMap.add identifier { runtime with state = Open; violations; opened_at_ns = now_ns; trips = saturating_add runtime.trips 1L } engine
        else RuleMap.add identifier { runtime with violations } engine

let advance_time engine now_ns =
  RuleMap.mapi (fun _ runtime ->
    if runtime.state = Open && not runtime.rule.manual_clear && Int64.compare now_ns runtime.opened_at_ns >= 0 && Int64.compare (Int64.sub now_ns runtime.opened_at_ns) runtime.rule.cooldown_ns >= 0 then { runtime with state = HalfOpen }
    else runtime) engine

let clear engine identifier =
  match RuleMap.find_opt identifier engine with
  | Some runtime when runtime.rule.manual_clear || runtime.state = HalfOpen -> RuleMap.add identifier { runtime with state = Closed; violations = 0L; opened_at_ns = 0L } engine
  | _ -> engine

let trip_count engine identifier =
  match RuleMap.find_opt identifier engine with
  | Some runtime -> runtime.trips
  | None -> 0L

let default_rule = { identifier = "CB-HF-001"; scope = Strategy; threshold = 1000L; cooldown_ns = 10_000L; manual_clear = true }

let () =
  let engine = install empty default_rule in
  let engine = Array.fold_left (fun current index -> observe current "CB-HF-001" 1L (Int64.of_int index)) engine (Array.init 100_000 (fun index -> index)) in
  let engine = apply_update engine (Replace { default_rule with threshold = 50_000L }) in
  let engine = clear engine "CB-HF-001" in
  let engine = observe engine "CB-HF-001" 50_000L 200_000L in
  let output = match state engine "CB-HF-001" with Some Open -> "dynamic_policy_open" | Some Closed -> "dynamic_policy_closed" | Some HalfOpen -> "dynamic_policy_half_open" | None -> "dynamic_policy_missing" in
  print_endline (output ^ ":" ^ Int64.to_string (trip_count engine "CB-HF-001"))
