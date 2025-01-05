open Yojson.Basic.Util
open Types

let parse_json file =
  try
    let name = file |> member "name" |> to_string in
    { name }
  with
  | Yojson.Basic.Util.Type_error (msg, _) ->
    failwith ("Type error: " ^ msg)

