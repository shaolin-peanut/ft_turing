open Parser

let () =
  let machine_name = "machines/unary_sub.json" in
  (* let json = Yojson.Basic.from_file ("machines/" ^ machine_name ^ ".json") in *)
  (* print_endline (Yojson.Basic.pretty_to_string json); *)
  let machine = Parser.parse_json machine_name;
  in print_endline machine.name;
  print_endline (String.concat ", " machine.alphabet)
