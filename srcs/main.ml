open Parser
open Compute


let print_usage () =
  Printf.printf "usage: ft_turing [-h] jsonfile input\n\n";
  Printf.printf "positional arguments:\n";
  Printf.printf "  jsonfile   json description of the machine\n";
  Printf.printf "  input      input of the machine\n\n";
  Printf.printf "optional arguments:\n";
  Printf.printf "  -h, --help show this help message and exit\n\n"


  let string_to_list str =
  let rec aux i acc = 
    if i < String.length str then
      aux (i + 1) (acc @ [String.make 1 str.[i]])  (* Convert each character into a string and collect *)
    else acc
  in aux 0 []

let () =

(* Handle the help command *)
  if Array.length Sys.argv > 1 && (Sys.argv.(1) = "--help" || Sys.argv.(1) = "--h") then
    begin
      print_usage ();
      exit 0
    end;

  (* Ensure enough positional arguments are provided *)
  if Array.length Sys.argv < 3 then
    begin
      Printf.eprintf "Error: Missing required arguments.\n Type --help for informations";
      exit 1 
    end;

let machine_name = Sys.argv.(1) in
let input_string = Sys.argv.(2) in  (* Get the input as a single string *)

(* Convert the input string into a list of strings *)
let input_list = string_to_list input_string in

(* Parse the machine JSON and run it *)
let machine = Parser.parse_json machine_name in
let input = Parser.parse_input input_list machine.alphabet machine.blank in

(* Run the machine with the converted input list *)
let output = Compute.run_machine machine input false  in
  (* Print the output *)
  List.iter (fun s -> Printf.printf "%s\n" s) output

