open Yojson.Basic.Util
open Types

(* 
-> helper function to parse alphabet
1. only strings of only one character
2. no duplicates
3. no empty strings
 *)
let parse_alphabet alphabet =
  let rec loop = function
    | [] -> []
    | hd :: tl ->
      if String.length hd = 1 && not (List.mem hd tl) then
        hd :: loop tl
      else
        failwith "Invalid alphabet"
  in
  loop alphabet


(*
-> helper function to check if blank character is in alphabet
  TODO: check that blank charcter is not part of the input @Marie
 *)
let check_blank_char char alphabet = 
  if List.mem char alphabet then
    char
  else
    failwith "Invalid blank character"

(*
-> helper funciton to validate states 
*)
let check_states states = 
  let rec loop = function
    | [] -> []
    | hd :: tl ->
      if not (List.mem hd tl) then
        hd :: loop tl
      else
        failwith "Invalid states"
  in
  loop states

(*
-> helper function to check if initial state is part of the given states
*)
let check_initial_state initial states = 
  if List.mem initial states then
    initial
  else
    failwith "Invalid initial state"


(* 
-> helper function to check if the final states are part of the given states
 *)
let check_final_states finals states = 
  let rec loop = function
    | [] -> []
    | hd :: tl ->
      if List.mem hd states && not (List.mem hd tl) then
        hd :: loop tl
      else
        failwith "Invalid final states"
  in
  loop finals

  let extract_transitions json =
    let transitions_json = json |> member "transitions" in
    let transitions_list = transitions_json |> keys |> List.map (fun state ->
      let trans_list = transitions_json |> member state |> to_list in
      let transition_list = List.map (fun trans ->
        {
          read = trans |> member "read" |> to_string;
          to_state = trans |> member "to_state" |> to_string;
          write = trans |> member "write" |> to_string;
          action = trans |> member "action" |> to_string;
        }) trans_list
      in
      (state, transition_list)
    ) in
    transitions_list


let extract_json file =
  let name = file |> member "name" |> to_string in
  let alphabet = file |> member "alphabet" |> to_list |> List.map to_string in
  let blank = file |> member "blank" |> to_string in
  let states = file |> member "states" |> to_list |> List.map to_string in
  let initial = file |> member "initial" |> to_string in
  let finals = file |> member "finals" |> to_list |> List.map to_string in
  (name, alphabet, blank, states, initial, finals)


  let extract_states_name transitions =
    List.map fst transitions 

(*
-> transition's names shoulde be part of the states 
 *)
let check_transitions_names transitions_names states =
  let rec loop = function
  | [] -> ()
  | hd :: tl -> 
    if List.mem hd states then
      loop tl
    else
      failwith ("Transition '" ^ hd ^ "' does not match any state")
    in
    loop transitions_names

let check_transitions_read_and_write_char transition_list alphabet =
  let rec loop = function
  | [] -> () 
    | hd :: tl ->
      if List.mem hd.read alphabet && List.mem hd.write alphabet then
        loop tl
      else
        failwith ("Invalid read or write character: read='" ^ hd.read ^ "' write='" ^ hd.write ^ "'")
  in 
  loop transition_list

(* 
-> the to_state of the transition should be part of the states
  *)
let check_transitions_to_state transition_list states =
  let rec loop = function
  | [] -> ()
  | hd :: tl ->
    if List.mem hd.to_state states then
      loop tl
    else
      failwith ("Transition to state '" ^ hd.to_state ^ "' does not match any state")
  in
  loop transition_list


(* 
-> the action of the transition should be either "LEFT" or "RIGHT"
 *)
  let check_transitions_action transition_list =
    let valid_actions = ["LEFT"; "RIGHT"] in  (* Define valid action values *)
    
    let rec loop = function
      | [] -> () 
      | hd :: tl ->
        if List.mem hd.action valid_actions then
          loop tl  
        else
          failwith ("Invalid action: " ^ hd.action) 
    
    in
    loop transition_list 

(* 
-> helper function to parse the transitions
 *)
let parse_transitions transitions states alphabet =
  let transitions_names = extract_states_name transitions in
  check_transitions_names transitions_names states;

  let transition_list = List.flatten (List.map snd transitions) in
  check_transitions_read_and_write_char transition_list alphabet;
  check_transitions_to_state transition_list states;
  check_transitions_action transition_list;
  transitions


let parse_json file =
    try
      let json = Yojson.Basic.from_file file in
      let (name, alphabet, blank, states, initial, finals) = extract_json json in
      let transitions_json = extract_transitions json in
      {
        name = name;
        alphabet = parse_alphabet alphabet;
        blank = check_blank_char blank alphabet;
        states = check_states states;
        initial = check_initial_state initial states;
        finals = check_final_states finals states;
        transitions = parse_transitions transitions_json states alphabet
      }
    with
    | Yojson.Basic.Util.Type_error (msg, _) ->
      failwith ("Type error: " ^ msg)
    | Yojson.Json_error msg ->
      failwith ("JSON error: " ^ msg)

