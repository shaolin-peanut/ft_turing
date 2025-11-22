(* srcs/encoder.ml *)
open Types

(* --- Fonctions utilitaires --- *)

let get_unary n = String.make n 'b'
let get_c_block n = String.make n 'c'

(* Trouve l'index (1-based) d'un élément dans une liste *)
let index_of lst elem =
  let rec aux i = function
    | [] -> failwith ("Element not found: " ^ elem)
    | h :: t -> if h = elem then i else aux (i + 1) t
  in aux 1 lst

(* --- Constantes U9,3 --- *)
let s_const = "cc"
let g_const = "X"
let v_const = "dcc"     (* Avant: "d c c " *)
let h_const = "becbc"   (* Avant: "becbc " *)

(* --- Main --- *)
let () =
  if Array.length Sys.argv <> 3 then begin
    Printf.printf "Usage: %s <machine.json> <input_string>\n" Sys.argv.(0);
    exit 1
  end;

  let filename = Sys.argv.(1) in
  let input_str = Sys.argv.(2) in

  (* 1. On utilise TON parser existant *)
let machine = Parser.parse_json filename in

  (* On recupère les listes pour les index *)
  let alphabet = machine.alphabet in
  let states = machine.states in
  let q = List.length alphabet in

  (* Note: On suppose que le dernier état est HALT et on l'exclut des règles de transition
     comme dans le script Python. *)
  let active_states = List.rev (List.tl (List.rev states)) in

  (* 2. Génération des Règles (Partie Gauche) *)
  (* Structure : H + [Transitions] + V^2 + [Identité] + V^3 *)
  
  print_string h_const;

  (* A. Les Transitions P(e_j, a_i) *)
  (* On itère à l'envers sur les états et l'alphabet *)
  List.iter (fun state ->
    let state_idx = index_of states state in
    List.iter (fun sym ->
      let sym_idx = index_of alphabet sym in
      
      (* On cherche la transition correspondante dans la liste de la machine *)
      (* Rappel: machine.transitions est une liste de (key, action) *)
      let trans_opt = List.find_opt (fun (k, _) -> 
        k.state = state && k.symbol = sym
      ) machine.transitions in

      match trans_opt with
      | Some (_, action) ->
          let next_state_idx = index_of states action.next_state in
          let write_sym_idx = index_of alphabet action.write in
          
          (* FORMULE U9,3 Table 2 *)
          Printf.printf "dccdd%sd%s%s"
            (get_c_block (8 * next_state_idx * q + 2))
            (get_c_block (8 * write_sym_idx))
            v_const
      | None -> () (* Pas de transition définie, on saute *)

    ) (List.rev alphabet)
  ) (List.rev active_states);

  print_string v_const;

  (* B. Les Identités P(a_i) *)
  List.iter (fun sym ->
    let sym_idx = index_of alphabet sym in
    (* FORMULE U9,3 Table 2 colonne P(ai) *)
    Printf.printf "ddccd%s%s"
      (get_c_block (8 * sym_idx))
      v_const
  ) (List.rev alphabet);

  print_string v_const;

  (* 3. Génération des Données (Partie Droite) *)
  (* Structure : S + G + [Etat Initial] + [Bande Input] *)
  
  Printf.printf "%s%s" s_const g_const;

  (* Etat initial *)
  let init_idx = index_of states machine.initial in
  Printf.printf "%s" (get_unary (4 * init_idx * q));

  (* Bande d'entrée *)
  String.iter (fun c ->
    let char_str = String.make 1 c in
    let sym_idx = index_of alphabet char_str in
    Printf.printf "%sd" (get_unary (4 * sym_idx - 1))
  ) input_str;

  print_string "ccc\n"