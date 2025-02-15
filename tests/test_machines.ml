open Test_utils 
open Parser
open Compute


(* TODO: move in a folder 'utils' *)
let string_to_list str =
  let rec aux i acc = 
    if i < String.length str then
      aux (i + 1) (acc @ [String.make 1 str.[i]])  (* Convert each character into a string and collect *)
    else acc
  in aux 0 []


let remove_char ch str =
  let buffer = Buffer.create (String.length str) in  (* Create a buffer to construct result *)
  String.iter (fun c -> if c <> ch then Buffer.add_char buffer c) str;  (* Add characters to buffer if they are not equal to ch *)
  Buffer.contents buffer  (* Convert the buffer back to a string *)

  let run_machine_test machine_name input expected_output =
    (* Print input and expected output *)
    print_endline "";
    Printf.printf "Input:           %s\n" input;
    Printf.printf "Expected Output: %s\n" expected_output;
  
    (* Parse the machine from the JSON file *)
    let machine = Parser.parse_json machine_name in
    let blank_to_char = String.get machine.blank 0 in
  
    (* Parse input using your defined logic *)
    let input_list = Parser.parse_input (string_to_list input) machine.alphabet machine.blank in
    
    (* Run the machine and capture output *)
    let output = Compute.run_machine machine input_list false in
  
    (* Get the last output as a string *)
    let last_output = List.hd (List.rev output) in  (* This is the last output line *)
  
    let parsed_output_from_space = remove_char ' ' last_output in
    let parsed_out_from_blank = remove_char blank_to_char parsed_output_from_space in
  
    (* Print the output *)
    Printf.printf "Output:          %s\n" parsed_out_from_blank;

    (* Ensure the last output is a string for comparison and assert *)
    assert (String.trim(parsed_out_from_blank) = expected_output)

let test_run_machine_unary_sub () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in
  
  print_endline (yellow ^ "\nRunning tests for unary_sub machine" ^ reset);
  test "Test 1" (fun () ->
    print_endline "\nTest 1\n";
    run_machine_test "machines/unary_sub.json" "111-11=" "1" 
  )
  (* test "Test 2" (fun () ->
    print_endline "\nTest 2\n";
    run_machine_test "machines/unary_sub.json" "1 1 1 - 1 1 1 1 =" ". . . . . . . ."
  ) *)
  (* test "Test 3" (fun () ->
    print_endline "\nTest 3\n";
    run_machine_test "machines/unary_sub.json" "- 1 =" ". . . . . . . ."
  ) *)

let test_run_machine_unary_add () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in
  
  print_endline (yellow ^ "\nRunning tests for unary_add machine" ^ reset);
  test "Test 1" (fun () ->
    run_machine_test "machines/unary_add.json" "11+11=" "1111"
  );

  test "Test 2" (fun () ->
    run_machine_test "machines/unary_add.json" "111+11" "1111"
  );

  test "Test 3 (edge case)" (fun () ->    
    (* TODO: change the machine to handle this case ?? *)
    run_machine_test "machines/unary_add.json" "11+=" "11"
  );

  test "Test 4 (edge case) " (fun () ->
    (* TODO: change the machine to handle this case ?? *)
    run_machine_test "machines/unary_add.json" "+1=" "1"
  )


let test_run_machine_palindrome () =
  let yellow = "\027[33m" in
  let cyan = "\027[36m" in
  let reset = "\027[0m" in

  print_endline (yellow ^ "\nRunning tests for palindrome machine" ^ reset);
  test "Test 1" (fun () ->
    run_machine_test "machines/palindrome.json" "101" "y"
  );

  test "Test 2" (fun () ->
    run_machine_test "machines/palindrome.json" "010" "y"
  );

  test "Test 3" (fun () ->
    run_machine_test "machines/palindrome.json" "111" "y"
  );

  test "Test 4" (fun () ->
    run_machine_test "machines/palindrome.json" "000" "y"
  );

  test "Test 5" (fun () ->
    run_machine_test "machines/palindrome.json" "1001" "y"
  );

  test "Test 6" (fun () ->
    run_machine_test "machines/palindrome.json" "0110" "y"
  );

  test "Test 7" (fun () ->
    run_machine_test "machines/palindrome.json" "1100" "10n"
  );

  test "Test 8" (fun () ->
    run_machine_test "machines/palindrome.json" "0011" "01n"
  );

  test "Test 9" (fun () ->
    run_machine_test "machines/palindrome.json" "1010" "01n"
  );

  test "Test 10" (fun () ->
    run_machine_test "machines/palindrome.json" "0101" "10n"
  );

  test "Test 11" (fun () ->
    run_machine_test "machines/palindrome.json" "1" "y"
  );

  test "Test 12" (fun () ->
    run_machine_test "machines/palindrome.json" "0" "y"
  )

let test_run_machine_balanced_binary () =
  let yellow = "\027[33m" in
  let reset = "\027[0m" in
  let filename = "machines/balanced_binary.json" in

  print_endline (yellow ^ "\nRunning tests for balanced_binary machine" ^ reset);
 (* Valid cases (should output 'y') *)
 test "Test 1 (Invalid: 1)" (fun () ->
  run_machine_test filename "1" "1n"
  );
  test "Test 2 (Valid: 01)" (fun () ->
    run_machine_test filename "01" "y"
  );
  test "Test 3 (Valid: 0011)" (fun () ->
    run_machine_test filename "0011" "y"
  );
  test "Test 4 (Valid: 000111)" (fun () ->
    run_machine_test filename "000111" "y"
  );
  test "Test 5 (Valid: 00001111)" (fun () ->
    run_machine_test filename "00001111" "y"
  );

  (* Invalid cases (should output 'n') *)
  test "Test 6 (Invalid: 11)" (fun () ->
    run_machine_test filename "11" "11n"
  );
  test "Test 7 (Invalid: 00011)" (fun () ->
    run_machine_test filename "00011" "n"
  );
  test "Test 8 (Invalid: 0001111)" (fun () ->
    run_machine_test filename "0001111" "1n"
  );
  test "Test 9 (Invalid: 10)" (fun () ->
    run_machine_test filename "10" "10n"
  );
  test "Test 10 (Invalid: 0)" (fun () ->
    run_machine_test filename "0" "n"
  );

  test "Test 11 (Invalid: 111)" (fun () ->
    run_machine_test filename "111" "111n"
  );

  test "Test 12b (Invalid: 1111111)" (fun () ->
    run_machine_test filename "1111111" "1111111n"
  );

  test "Test 12 (Invalid: 000010111)" (fun () ->
    run_machine_test filename "000010111" "10n"
  );

  test "Test 13 (Invalid: 000011111)" (fun () ->
    run_machine_test filename "000011111" "1n"
  )

let () =
    test_run_machine_unary_sub (); 
    (* test_run machine_unary_add ();   *)
    test_run_machine_palindrome();
    test_run_machine_balanced_binary();
    run_tests ()