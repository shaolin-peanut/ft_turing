open Types

type tape = {
  current: string;
  left: string list;
  right: string list;
}

let halts symbol finals =
  List.mem symbol finals

let hd_or_blank blank lst =
  match lst with
  | [] -> blank
  | hd :: _ -> hd

let tl_or_empty blank lst =
  match lst with
  | [] -> [blank] 
  | _ -> List.tl lst

let shift_tape blank direction tape =
  match direction with
  | Left -> {
      current = hd_or_blank blank tape.left;
      left = tl_or_empty blank tape.left;
      right = tape.current :: tape.right;
      }
  | Right -> {
      current = hd_or_blank blank tape.right;
      left = tape.current :: tape.left;
      right = tl_or_empty blank tape.right;
  }

(* --- UTILS FOR OUTPUT --- *)

(* Helper to take first N items of a list *)
let rec take n lst =
  if n <= 0 then []
  else match lst with
  | [] -> []
  | h :: t -> h :: take (n-1) t

(* Full Tape (Slow, Use only for final result) *)
let output_final_tape tape =
  let buf = Buffer.create 1000 in
  let rec add_left = function
    | [] -> ()
    | h :: t -> add_left t; Buffer.add_string buf h; Buffer.add_char buf ' '
  in
  add_left tape.left;
  Buffer.add_string buf tape.current;
  List.iter (fun s -> Buffer.add_char buf ' '; Buffer.add_string buf s) tape.right;
  Buffer.contents buf

(* Lightweight Tape (Fast, Use for checkpoints) *)
(* Shows: ... [200 chars left] >[HEAD]< [200 chars right] ... *)
let output_debug_tape tape =
  let buf = Buffer.create 500 in
  
  Buffer.add_string buf "... ";
  
  (* Left is reversed, so we take 200, then reverse them to print correctly *)
  let left_part = take 200 tape.left |> List.rev in
  List.iter (fun s -> Buffer.add_string buf s; Buffer.add_char buf ' ') left_part;
  
  Buffer.add_string buf " >[";
  Buffer.add_string buf tape.current;
  Buffer.add_string buf "]< ";
  
  let right_part = take 200 tape.right in
  List.iter (fun s -> Buffer.add_string buf s; Buffer.add_char buf ' ') right_part;
  
  Buffer.add_string buf " ...";
  Buffer.contents buf

let save_checkpoint filename tape state step =
  let oc = open_out filename in
  Printf.fprintf oc "Step: %d | State: %s\n" step state;
  (* Use the FAST output function *)
  Printf.fprintf oc "%s\n" (output_debug_tape tape);
  close_out oc

(* --- MAIN RUNNER --- *)

let run_machine (machine : turing_machine) (input : string list) print_steps : unit =
  
  let rules = Hashtbl.create (List.length machine.transitions) in
  List.iter (fun (k, action) -> 
    Hashtbl.add rules (k.state, k.symbol) action
  ) machine.transitions;

  let get_action current_state current_symbol =
    Hashtbl.find_opt rules (current_state, current_symbol)
  in
  
  let rec compute current_state (tape : tape) step_count =
    
    (* DEBUG: Initial Proof of Life *)
    if step_count = 1 then (
       save_checkpoint "debug_start.txt" tape current_state step_count;
    );

    (* CHECKPOINT: Now fast enough to run every 1 Million steps *)
    if step_count > 0 && (step_count mod 1000000 = 0) then (
       save_checkpoint "checkpoint.txt" tape current_state step_count;
       Printf.eprintf "\r[Checkpoint @ %dM steps] " (step_count / 1000000);
       flush stderr
    );

    if halts current_state machine.finals then (
      let final_tape = output_final_tape tape in
      Printf.printf "%s\n" final_tape;
      flush stdout
    ) else (
      match get_action current_state tape.current with
      | None -> 
          Printf.eprintf "\n[HALT] Undefined transition (Crash Halt).\n";
          let final_tape = output_final_tape tape in
          Printf.printf "%s\n" final_tape;
          flush stdout
      | Some action ->
          let next_tape =
            {tape with current = action.write} 
            |> shift_tape machine.blank action.move
          in
          compute action.next_state next_tape (step_count + 1)
    )
  in
  
  let starting_tape = match input with
    | [] -> { current = ""; left = []; right = [] }
    | hd::tl -> { current = hd; left = []; right = tl }
  in
  compute machine.initial starting_tape 0