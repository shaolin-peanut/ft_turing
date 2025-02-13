open Test_utils 
open Parser
open Compute

let string_to_list str =
  let words = String.split_on_char ' ' str in  (* Split the string by spaces *)
  List.filter (fun s -> s <> "") words

let run_machine_test machine_name input expected_output =
  (* Print input and expected output *)
  Printf.printf "Input:           %s\n" input;
  Printf.printf "Expected Output: %s\n" expected_output;
  
  (* Parse the machine from the JSON file *)
  let machine = Parser.parse_json machine_name in

  (* Parse input using your defined logic *)
  let input_list = Parser.parse_input (string_to_list input) machine.alphabet machine.blank in
  
  (* Run the machine and capture output *)
  let output = Compute.run_machine machine input_list false in

  (* Get the last output as a string *)
  let last_output = List.hd (List.rev output) in  (* This is the last output line *)

  (* Print the output *)
  Printf.printf "Output:          %s\n" last_output;
  
  (* Ensure the last output is a string for comparison and assert *)
  assert (last_output = expected_output)

let test_run_machine_unary_sub () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in
  
  print_endline (yellow ^ "\nRunning tests for unary_sub machine" ^ reset);
  test "Test 1" (fun () ->
    print_endline "\nTest 1\n";
    run_machine_test "machines/unary_sub.json" "1 1 1 - 1 1 =" "1 . . . . . ." 
  );
  test "Test 2" (fun () ->
    print_endline "\nTest 2\n";
    run_machine_test "machines/unary_sub.json" "1 1 1 - 1 1 1 =" ". . . . . . . ."
  )
  (* test "Test 3" (fun () ->
    print_endline "\nTest 3\n";
    run_machine_test "machines/unary_sub.json" "- 1 =" ". . . . . . . ."
  ) *)

let test_run_machine_unary_add () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in
  
  print_endline (yellow ^ "\nRunning tests for unary_add machine" ^ reset);
  test "Test 1" (fun () ->
    run_machine_test "machines/unary_add.json" "1 1 + 1 1 =" "1 1 1 1 . ."
  );

  test "Test 2" (fun () ->
    run_machine_test "machines/unary_add.json" "1 1 1 + 1 1 1 =" "1 1 1 1 1 1 . ."
  );

  test "Test 3" (fun () ->
    run_machine_test "machines/unary_add.json" "+ 1 1 =" "1 1 . ."
  );

  test "Test 4" (fun () ->
    run_machine_test "machines/unary_add.json" "1 1 + =" "1 1 . ."
  )


let test_run_machine_palindrome () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in

  print_endline (yellow ^ "\nRunning tests for palindrome machine" ^ reset);
  test "Test 1" (fun () ->
    run_machine_test "machines/palindrome.json" "1 0 1" ". y . . ."
  );

  test "Test 2" (fun () ->
    run_machine_test "machines/palindrome.json" "0 1 0" ". y . . ."
  );

  test "Test 3" (fun () ->
    run_machine_test "machines/palindrome.json" "1 1 1" ". y . . ."
  );

  test "Test 4" (fun () ->
    run_machine_test "machines/palindrome.json" "0 0 0" ". y . ."
  );

  test "Test 5" (fun () ->
    run_machine_test "machines/palindrome.json" "1 0 0 1" ". . y . . ."
  );

  test "Test 6" (fun () ->
    run_machine_test "machines/palindrome.json" "0 1 1 0" ". . y . . ."
  )



(* NOTE:
    - for readability sake the "input" are passed to run_machine_test with space (easier to read and compare with output)
    but they are parsed before being passed to run_machine_test
    ex: "1 1 1 - 1 1 1 =" is parsed to ["1"; "1"; "1"; "-"; "1"; "1"; "1"; "="]
 *)
let () =
    test_run_machine_unary_sub (); 
    test_run_machine_unary_add ();  
    test_run_machine_palindrome();
    run_tests ()