open Test_utils
open Parser

let test_parse_alphabet () =

  print_endline "\nTesting parse_alphabet";
  (* Test 1: Valid alphabet *)
  let () =
    test "Valid alphabet" (fun () ->
      let input = ["a"; "b"; "c"] in
      let result = parse_alphabet input in
      assert (result = ["a"; "b"; "c"])
    )
  in

  (* Test 2: Duplicate symbols *)
  let () =
    test "Duplicate symbols" (fun () ->
      let input = ["a"; "b"; "a"] in
      try
        let _ = parse_alphabet input in
        failwith "Expected failure for duplicate symbols"
      with
      | Failure "Invalid alphabet" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 3: Invalid length *)
  let () =
    test "Invalid length" (fun () ->
      let input = ["a"; "bb"; "c"] in
      try
        let _ = parse_alphabet input in
        failwith "Expected failure for invalid length"
      with
      | Failure "Invalid alphabet" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 4: Empty alphabet *)
  let () =
    test "Empty alphabet" (fun () ->
      let input = [] in
      let result = parse_alphabet input in
      assert (result = [])
    ) in ()


let test_check_blank_char () =
  print_endline "\nTesting check_blank_char";
  (* Test 1: Valid blank character *)
  let () =
    test "Valid blank character" (fun () ->
      let input = "b" in
      let alphabet = ["a"; "b"; "c"] in
      let result = check_blank_char input alphabet in
      assert (result = "b")
    )
  in

  (* Test 2: Invalid blank character *)
  let () =
    test "Invalid blank character" (fun () ->
      let input = "d" in
      let alphabet = ["a"; "b"; "c"] in
      try
        let _ = check_blank_char input alphabet in
        failwith "Expected failure for invalid blank character"
      with
      | Failure "Invalid blank character" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 3: Empty alphabet *)
  let () =
    test "Empty alphabet" (fun () ->
      let input = "b" in
      let alphabet = [] in
      try
        let _ = check_blank_char input alphabet in
        failwith "Expected failure for empty alphabet"
      with
      | Failure "Invalid blank character" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 4: Empty blank character *)
  let () =
    test "Empty blank character" (fun () ->
      let input = "" in
      let alphabet = ["a"; "b"; "c"] in
      try
        let _ = check_blank_char input alphabet in
        failwith "Expected failure for empty blank character"
      with
      | Failure "Invalid blank character" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 5: Blank character not in alphabet *)
  let () =
    test "Blank character not in alphabet" (fun () ->
      let input = "d" in
      let alphabet = ["a"; "b"; "c"] in
      try
        let _ = check_blank_char input alphabet in
        failwith "Expected failure for blank character not in alphabet"
      with
      | Failure "Invalid blank character" -> ()
      | _ -> failwith "Wrong error message"
    )
  in ()

let test_check_machine_states () =

  print_endline "\nTesting check_states";

  (* Test 1: Valid states *)
  let () =
    test "Valid states" (fun () ->
      let input = ["q0"; "q1"; "q2"] in
      let result = check_states input in
      assert (result = ["q0"; "q1"; "q2"])
    )
  in

  (* Test 2: Duplicate states *)
  let () =
    test "Duplicate states" (fun () ->
      let input = ["q0"; "q1"; "q0"] in
      try
        let _ = check_states input in
        failwith "Expected failure for duplicate states"
      with
      | Failure "Invalid states" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 3: Empty states *)
  let () =
    test "Empty states" (fun () ->
      let input = [] in
      let result = check_states input in
      assert (result = [])
    ) in ()

let test_check_initial_state () =

  print_endline "\nTesting check_initial_state";

  (* Test 1: Valid initial state *)
  let () =
    test "Valid initial state" (fun () ->
      let input = "q0" in
      let states = ["q0"; "q1"; "q2"] in
      let result = check_initial_state input states in
      assert (result = "q0")
    )
  in

  (* Test 2: Invalid initial state *)
  let () =
    test "Invalid initial state" (fun () ->
      let input = "q3" in
      let states = ["q0"; "q1"; "q2"] in
      try
        let _ = check_initial_state input states in
        failwith "Expected failure for invalid initial state"
      with
      | Failure "Invalid initial state" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 3: Empty states *)
  let () =
    test "Empty states" (fun () ->
      let input = "q0" in
      let states = [] in
      try
        let _ = check_initial_state input states in
        failwith "Expected failure for empty states"
      with
      | Failure "Invalid initial state" -> ()
      | _ -> failwith "Wrong error message"
    )
  in ()

let test_check_final_states () =

  print_endline "\nTesting check_final_states";

  (* Test 1: Valid final states *)
  let () =
    test "Valid final states" (fun () ->
      let input = ["q0"; "q1"] in
      let states = ["q0"; "q1"; "q2"] in
      let result = check_final_states input states in
      assert (result = ["q0"; "q1"])
    )
  in

  (* Test 2: Duplicate final states *)
  let () =
    test "Duplicate final states" (fun () ->
      let input = ["q0"; "q1"; "q0"] in
      let states = ["q0"; "q1"; "q2"] in
      try
        let _ = check_final_states input states in
        failwith "Expected failure for duplicate final states"
      with
      | Failure "Invalid final states" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 3: Invalid final states *)
  let () =
    test "Invalid final states" (fun () ->
      let input = ["q0"; "q3"] in
      let states = ["q0"; "q1"; "q2"] in
      try
        let _ = check_final_states input states in
        failwith "Expected failure for invalid final states"
      with
      | Failure "Invalid final states" -> ()
      | _ -> failwith "Wrong error message"
    )
  in

  (* Test 4: Empty states *)
  let () =
    test "Empty states" (fun () ->
      let input = ["q0"; "q1"] in
      let states = [] in
      try
        let _ = check_final_states input states in
        failwith "Expected failure for empty states"
      with
      | Failure "Invalid final states" -> ()
      | _ -> failwith "Wrong error message"
    )
  in ()

    
let () =
  test_parse_alphabet ();
  test_check_blank_char ();
  test_check_machine_states ();
  test_check_initial_state ();
  test_check_final_states ();
  run_tests ()
