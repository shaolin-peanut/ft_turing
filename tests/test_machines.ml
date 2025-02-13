open Test_utils 
open Parser
open Compute

let string_to_list str =
  let rec aux i acc = 
    if i < String.length str then
      aux (i + 1) (acc @ [String.make 1 str.[i]])  (* Convert each character into a string and collect *)
    else 
      acc
  in aux 0 []

let run_machine_test machine_name input expected_output =
  (* Print input and expected output *)
  Printf.printf "Input: %s\n" input;
  Printf.printf "Expected Output: %s\n" expected_output;
  
  (* Parse the machine from the JSON file *)
  let machine = Parser.parse_json machine_name in

  (* Parse input using your defined logic *)
  let input_list = Parser.parse_input (string_to_list input) machine.alphabet machine.blank in
  
  (* Run the machine and capture output *)
  let output = Compute.run_machine machine input_list in

  (* Get the last output as a string *)
  let last_output = List.hd (List.rev output) in  (* This is the last output line *)

  (* Print the full output for clarity *)
  print_endline (String.concat "" output);  (* Print full output for inspection *)
  
  (* Ensure the last output is a string for comparison and assert *)
  assert (last_output = expected_output)

let test_run_machine_unary_sub () =
  test "Unary Subtraction Machine" (fun () ->
    run_machine_test "machines/unary_sub.json" "111-11=" "1......"  (* This should return unit *)
  )

let () =
    test_run_machine_unary_sub ();  (* Call the test function, wrapping it as a unit producing function *)
    run_tests ()