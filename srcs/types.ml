type name = string

type transition_json = {
  read: string;
  to_state: string;
  write: string;
  action: string;
}

type turing_machine_json = {
  name: name;
  alphabet: string list;
  blank: string;
  states: string list;
  initial: string;
  finals: string list;
  transitions: (string * transition_json list) list;
}


(* =============================================== *)


type direction = Left | Right

type action = {
  next_state: string;
  write: string;
  move: direction;
}

type key = {
  state: string;
  symbol: string;
}

(* map (state_name, symbol) to (action), for more efficient lookups *)
type transition = (key * action)

(* maybe should be renamed to config or something *)
type turing_machine = {
  name : string;
  alphabet : string list;
  blank : string;
  initial : string;
  finals : string list;
  transitions: transition list;
}

