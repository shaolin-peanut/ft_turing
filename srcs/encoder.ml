(* ************************************************************************** *)
(* Neary–Woods U9,3 encoder (with bootstrap X marker for utm_9_3_bootsrap.json) *)
(* ************************************************************************** *)

open Types

(* -------------------------- helpers -------------------------- *)

let b_run n = String.make n 'b'
let c_run n = String.make n 'c'

(* 1-based index *)
let index_of lst elem =
  let rec aux i = function
    | [] -> failwith ("Element not found: " ^ elem)
    | h :: t -> if h = elem then i else aux (i + 1) t
  in
  aux 1 lst

let find_transition (machine : turing_machine) (st : string) (sym : string) : action option =
  List.find_opt (fun (k, _) -> k.state = st && k.symbol = sym) machine.transitions
  |> Option.map snd

(* -------------------- Neary–Woods U9,3 constants -------------------- *)
(* Using 'd' as δ, as your UTM JSON does. *)
let delta = "d"
let v = "dcc"      (* V = δcc *)
let v2 = v ^ v     (* V^2 *)
let v3 = v ^ v ^ v (* V^3 *)
let h_const = "bccbc" (* H *)
let s_star = "cc"     (* S* = c^2 in Table 2 for U9,3 *)
let bootstrap_marker = "X"  (* BOOT scans for this *)

(* -------------------- U9,3 production encodings -------------------- *)
(* Table 1 (U9,3):
   hP(a_i)i = δδccδ c^(8i)
   hP(e_j,a_i)i for P(e_j,a_i)=a_k e_m:
     = δccδδ c^(8*m*q + 2) δ c^(8k)
*)

let enc_P_ai (i : int) : string =
  (* δδccδ c^(8i)  ->  "ddccd" + c^(8i) *)
  "ddccd" ^ c_run (8 * i)

let enc_P_ea_ak_em ~(m:int) ~(k:int) ~(q:int) : string =
  (* δccδδ c^(8*m*q + 2) δ c^(8k)
     -> "dccdd" + c^(8*m*q + 2) + "d" + c^(8k)
  *)
  "dccdd" ^ c_run (8 * m * q + 2) ^ "d" ^ c_run (8 * k)

(* -------------------- Dataword encoding -------------------- *)
(* We emit a BTS dataword in the "A M E A M A M ..." shape:
   - one leading blank cell as A (so the word starts with A, like Example 1),
   - then M (δ),
   - then the state symbol E (he_j),
   - then the tape symbols as A M A M ...
   Encodings from Table 2 (U9,3):
     ha_i = b^(4i - 1)
     he_j = b^(4jq)
     M    = δ
*)

let enc_ha (i:int) : string = b_run (4 * i - 1)
let enc_he ~(j:int) ~(q:int) : string = b_run (4 * j * q)

let explode_string (s:string) : string list =
  let rec aux i acc =
    if i >= String.length s then List.rev acc
    else aux (i+1) (String.make 1 s.[i] :: acc)
  in
  aux 0 []

(* -------------------------- main encode -------------------------- *)

let encode_for_u9_3_bootstrap (machine : turing_machine) (input_str : string) : string =
  let alphabet = machine.alphabet in
  let states = machine.states in
  let q = List.length alphabet in

  (* Convention: last state is the "halt symbol" e_h (matches your unary_add_forward.json) *)
  let halt_state =
    match List.rev states with
    | [] -> failwith "Machine has no states"
    | hd :: _ -> hd
  in
  let halt_idx = index_of states halt_state in

  let active_states = List.filter (fun s -> s <> halt_state) states in

  (* ---------- build hRi ---------- *)
  let transition_encodings =
    List.concat (
      List.map (fun st ->
        List.map (fun sym ->
          let sym_idx = index_of alphabet sym in

          (* Look up transition; if missing, make it "crash-halting":
             go to halt state and keep symbol. *)
          let act =
            match find_transition machine st sym with
            | Some a -> a
            | None -> { next_state = halt_state; write = sym; move = Right }
          in

          (* This encoder is for "forward-going"/clockwise machines only. *)
          (match act.move with
           | Left -> failwith ("Encoder only supports RIGHT moves (clockwise). Offending transition: " ^ st ^ " on " ^ sym)
           | Right -> ());

          let m = index_of states act.next_state in
          let k = index_of alphabet act.write in
          (* if the JSON has weirdness, guard indices *)
          if m < 1 || m > List.length states then failwith "Bad next_state index";
          if k < 1 || k > q then failwith "Bad write symbol index";

          enc_P_ea_ak_em ~m ~k ~q
        ) (List.rev alphabet)
      ) (List.rev active_states)
    )
  in

  let identity_encodings =
    List.map (fun sym ->
      let i = index_of alphabet sym in
      enc_P_ai i
    ) (List.rev alphabet)
  in

  let hRi =
    h_const
    ^ (String.concat v transition_encodings)
    ^ v2
    ^ (String.concat v2 identity_encodings)
    ^ v3
  in

  (* ---------- build dataword ---------- *)
  let blank_sym = machine.blank in
  let blank_idx = index_of alphabet blank_sym in

  (* Read input symbols as single-char strings; validate they are in the machine alphabet *)
  let input_syms = explode_string input_str in
  List.iter (fun s ->
    if not (List.mem s alphabet) then
      failwith ("Input contains symbol not in alphabet: " ^ s)
  ) input_syms;

  (* Pad with a couple of blank tape cells so a right-moving machine can step past '=' safely *)
  let pad_blanks = 2 in
  let padded_syms = input_syms @ (List.init pad_blanks (fun _ -> blank_sym)) in

  let init_idx = index_of states machine.initial in

  (* Dataword: <blankA> δ <E_init> <A1>δ <A2>δ ... *)
  let dataword =
    (enc_ha blank_idx) ^ delta
    ^ (enc_he ~j:init_idx ~q)
    ^ (String.concat "" (List.map (fun sym ->
         let i = index_of alphabet sym in
         (enc_ha i) ^ delta
       ) padded_syms))
  in

  (* Full tape:
     ccc  hRi  S*  X  dataword  ccc
     (the surrounding ccc gives some concrete "paper-like" slack; beyond that your interpreter
      provides '.' blanks and your UTM converts as needed)
  *)
  "ccc" ^ hRi ^ s_star ^ bootstrap_marker ^ dataword ^ "ccc"

(* -------------------------- entrypoint -------------------------- *)
(* Important: if this file is linked into ft_turing by your Makefile,
   we do NOT want it to run. Only run when the executable name is "encoder". *)
let () =
  let base = Filename.basename Sys.argv.(0) in
  let is_encoder =
    base = "encoder" || base = "encoder.exe"
  in
  if is_encoder then (
    if Array.length Sys.argv <> 3 then (
      Printf.eprintf "Usage: %s <machine.json> <input_string>\n" Sys.argv.(0);
      exit 1
    );
    let filename = Sys.argv.(1) in
    let input_str = Sys.argv.(2) in
    let machine = Parser.parse_json filename in
    let tape = encode_for_u9_3_bootstrap machine input_str in
    print_string tape;
    print_newline ();
  )