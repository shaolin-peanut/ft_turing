open Test_utils
open Parser

let test_parse_alphabet () =
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
    
    
let () =
  test_parse_alphabet ();
  run_tests ()