
let () =
  let machine_name = "unary_sub" in
  let json = Yojson.Basic.from_file ("machines/" ^ machine_name ^ ".json") in
  let machine1 = Transition.generate_machine json in
  Compute.run_machine machine1 ["-";"1"]
  |> List.iter print_endline