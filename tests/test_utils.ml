let test_count = ref 0
let passed_count = ref 0
let failed_count = ref 0

let test name f =
  let cyan = "\027[36m" in
  let reset = "\027[0m" in

  incr test_count;
  try
    f ();
    incr passed_count;
    Printf.printf "\027[32m[✓]\027[0m %s%s%s\n" cyan name reset
  with exn ->
    incr failed_count;
    Printf.printf "\027[31m[✗]\027[0m %s: %s%s%s\n" cyan name reset (Printexc.to_string exn)

let run_tests () =
  Printf.printf "\nRan %d tests:\n" !test_count;
  Printf.printf "\027[32m%d passed\027[0m, \027[31m%d failed\027[0m\n" !passed_count !failed_count;
  if !failed_count > 0 then exit 1