open Types

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