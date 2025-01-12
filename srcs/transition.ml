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

(** [build_transition_table] builds the transition table from the json *)
let build_transition_table (transitions : (string * Yojson.Basic.t) list) =
  transitions
  |> List.map (fun (name, transition) : transition list ->
    let open Yojson.Basic.Util in
    transition |> to_list |> List.map (fun transition ->
      let read = transition |> member "read" |> to_string in
      let next_state = transition |> member "to_state" |> to_string in
      let write = transition |> member "write" |> to_string in
      let move = transition |> member "action" |> to_string |> fun (x) ->
        if x = "LEFT" then Left else Right in
      let transition_key = {state = name; symbol = read} in
      let transition_action : action = {next_state; write; move} in
      (transition_key, transition_action)
    ))
    |> List.flatten


let generate_machine (machine : Yojson.Basic.t) =
  let open Yojson.Basic.Util in
  let name = machine |> member "name" |> to_string in
  let alphabet = machine |> member "alphabet" |> to_list |> List.map to_string in
  let blank = machine |> member "blank" |> to_string in
  let initial = machine |> member "initial" |> to_string in
  let finals = machine |> member "finals" |> to_list |> List.map to_string in
  let transitions = machine |> member "transitions" |> to_assoc |> build_transition_table in
  {name; alphabet; blank; initial; finals; transitions}

let print_list lst =
  lst
  |> List.map (fun s -> Printf.sprintf "%s" s)
  |> String.concat ", "

let print_direction = function
  | Left -> "LEFT"
  | Right -> "RIGHT"

let print_transition (key, action) =
  Printf.sprintf "(%s, %s) -> (%s, %s, %s)"
    key.state key.symbol action.next_state action.write (print_direction action.move)

(* Print the Turing machine details *)
let print_machine (machine : turing_machine) =
  let transitions = 
    machine.transitions
    |> List.map print_transition
    |> String.concat "\n"
  in
  Printf.sprintf
    {|
********************************************************************************
*                                                                              *
* %s
*                                                                              *
********************************************************************************
Alphabet: [ %s ]
States   : [ %s ]
Initial  : %s
Finals   : [ %s ]
%s
********************************************************************************
|}
    machine.name
    (print_list machine.alphabet)
    (print_list (List.map (fun (key, _) -> key.state) machine.transitions |> List.sort_uniq compare))
    machine.initial
    (print_list machine.finals)
    transitions


(*
"scanright": [
  {
    "read": ".",
    "to_state": "scanright",
    "write": ".",
    "action": "RIGHT"
  },
  {
    "read": "1",
    "to_state": "scanright",
    "write": "1",
    "action": "RIGHT"
  },
  {
    "read": "-",
    "to_state": "scanright",
    "write": "-",
    "action": "RIGHT"
  },
  { "read": "=", "to_state": "eraseone", "write": ".", "action": "LEFT" }
],
"eraseone": [
  { "read": "1", "to_state": "subone", "write": "=", "action": "LEFT" },
  { "read": "-", "to_state": "HALT", "write": ".", "action": "LEFT" }
],
"subone": [
  { "read": "1", "to_state": "subone", "write": "1", "action": "LEFT" },
  { "read": "-", "to_state": "skip", "write": "-", "action": "LEFT" }
],
"skip": [
  { "read": ".", "to_state": "skip", "write": ".", "action": "LEFT" },
  {
    "read": "1",
    "to_state": "scanright",
    "write": ".",
    "action": "RIGHT"
  }
]
}*)