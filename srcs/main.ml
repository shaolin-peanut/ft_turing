open Parser
open Types

let print_transition trans =
  Printf.printf "{ read: %s; to_state: %s; write: %s; action: %s }\n"
    trans.read trans.to_state trans.write trans.action

let print_transitions_for_state (state, transitions) =
  Printf.printf "State: %s\n" state;
  List.iter print_transition transitions

let print_all_transitions transitions_list =
  List.iter print_transitions_for_state transitions_list

let () =
  let machine_name = "machines/unary_sub.json" in
  (* let json = Yojson.Basic.from_file ("machines/" ^ machine_name ^ ".json") in *)
  (* print_endline (Yojson.Basic.pretty_to_string json); *)
  let machine = Parser.parse_json machine_name;
  in print_endline machine.name;
  print_endline (String.concat ", " machine.alphabet);
  print_endline machine.blank;
  print_endline (String.concat ", " machine.states);
  print_endline machine.initial;
  print_endline (String.concat ", " machine.finals);
  print_all_transitions machine.transitions;
