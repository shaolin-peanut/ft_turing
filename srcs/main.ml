open Parser
open Compute

let print_usage () =
  Printf.printf "usage: ft_turing jsonfile input [--quiet]\n";
  Printf.printf "  jsonfile   json description of the machine\n";
  Printf.printf "  input      input of the machine\n";
  Printf.printf "  --quiet    disable progress bar\n"

let string_to_list str =
  let rec aux i acc = 
    if i < String.length str then
      aux (i + 1) (acc @ [String.make 1 str.[i]])
    else acc
  in aux 0 []

let () =
  if Array.length Sys.argv < 3 then begin
    print_usage ();
    exit 1 
  end;

  let machine_name = Sys.argv.(1) in
  let input_string = Sys.argv.(2) in
  
  (* Check for quiet flag *)
  let quiet = (Array.length Sys.argv > 3 && Sys.argv.(3) = "--quiet") in
  let print_steps = not quiet in

  let input_list = string_to_list input_string in
  let machine = Parser.parse_json machine_name in
  let input = Parser.parse_input input_list machine.alphabet machine.blank in

  (* Print Machine Info only if not quiet *)
  if not quiet then 
    Printf.printf "%s\n" (Transition.print_machine machine);

  (* Run *)
  Compute.run_machine machine input print_steps