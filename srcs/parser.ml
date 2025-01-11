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


(*
-> helper function to check if blank character is in alphabet
 *)
let check_blank_char char alphabet = 
  if List.mem char alphabet then
    char
  else
    failwith "Invalid blank character"


let extract_json file =
  let name = file |> member "name" |> to_string in
  let alphabet = file |> member "alphabet" |> to_list |> List.map to_string in
  let blank = file |> member "blank" |> to_string in
  (name, alphabet, blank)

let parse_json file =
    try
      let json = Yojson.Basic.from_file file in
      let (name, alphabet, blank) = extract_json json in
      {
        name = name;
        alphabet = parse_alphabet alphabet;
        blank = check_blank_char blank alphabet
      }
      (* {
        name = json |> member "name" |> to_string;
        alphabet = json |> member "alphabet" |> to_list |> List.map to_string |> parse_alphabet;
        blank = json |> member "blank" |> to_string |> check_blank_char (json |> member "blank" |> to_string) (json |> member "alphabet" |> to_list |> List.map to_string)
      } *)
    with
    | Yojson.Basic.Util.Type_error (msg, _) ->
      failwith ("Type error: " ^ msg)
    | Yojson.Json_error msg ->
      failwith ("JSON error: " ^ msg)

