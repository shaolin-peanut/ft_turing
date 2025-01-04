
let () =
  let machine_name = "unary_sub" in
  let json = Yojson.Basic.from_file ("machines/" ^ machine_name ^ ".json") in
  print_endline (Yojson.Basic.pretty_to_string json)
