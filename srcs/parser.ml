open Yojson.Basic.Util
open Types

(* 
-> helper function to parse alphabet
1. only strings of only one character
2. no duplicates
3. no empty strings
 *)
let parse_alphabet alphabet =
  let rec loop = function
    | [] -> []
    | hd :: tl ->
      if String.length hd = 1 && not (List.mem hd tl) then
        hd :: loop tl
      else
        failwith "Invalid alphabet"
  in
  loop alphabet

let parse_json file =
    try
      let json = Yojson.Basic.from_file file in
      {
        name = json |> member "name" |> to_string;
        alphabet = json |> member "alphabet" |> to_list |> List.map to_string;
      }
    with
    | Yojson.Basic.Util.Type_error (msg, _) ->
      failwith ("Type error: " ^ msg)
    | Yojson.Json_error msg ->
      failwith ("JSON error: " ^ msg)

