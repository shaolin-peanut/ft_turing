open Types

type tape = {
  current: string;
  left: string list;
  right: string list;
}

(** [halts] check if the symbol is a part of the halting symbols*)
let halts symbol finals =
  List.mem symbol finals
  (* finals |> List.mem symbol *)

  let hd_or_blank blank lst =
    match lst with
    | [] -> blank
    | hd :: _ -> hd
  
  let tl_or_empty blank lst =
    match lst with
    | [] -> [blank]  (* Append blank when reaching the end *)
    | _ -> List.tl lst

(** [shift_tape] shifts the tape according to the direction *)
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

let print_tape_and_state tape (transition : transition) =
  let red = "\027[31m" in 
  let green = "\027[32m" in 
  let reset = "\027[0m" in 


  let transition_str = Transition.print_transition transition in
  let left_str = 
    tape.left 
    |> List.rev
    |> List.map (fun s -> s ^ " ")
    |> String.concat ""
  in
  let right_str =
    tape.right
    |> List.map (fun s -> " " ^ s)
    |> String.concat ""
  in
  let tape_str = red ^ left_str ^ green ^ "[" ^ tape.current ^ "]" ^ red ^ right_str ^ reset in
  Printf.sprintf "%s\n%s" tape_str transition_str


let print_final_tape tape =
  let yellow = "\027[33m" in
  let left_str = 
    tape.left 
    |> List.rev
    |> List.map (fun s -> s ^ " ")
    |> String.concat ""
  in
  let right_str =
    tape.right
    |> List.map (fun s -> " " ^ s)
    |> String.concat ""
  in
  let tape_str = yellow ^ left_str ^ tape.current ^ right_str in
  Printf.sprintf "\n%s%s\n" "final tape: " tape_str
    
  (** [run_machine] take the config of a turing machine,
  places the input string on the tape and runs the turing machine  *)
  let run_machine (machine : turing_machine) (input : string list) : string list =
    let get_action key =
      match machine.transitions |> List.find_opt (fun (k, _) ->
        k.state = key.state && k.symbol = key.symbol) with
      | Some (_, action) -> action
      | None -> failwith ("No transition defined for state " ^ key.state ^ " and symbol " ^ key.symbol)
    in
    
    let rec compute current_state (tape : tape) output =

      if halts current_state machine.finals then
        print_endline (print_final_tape tape) |> fun _ ->
        List.rev output
      else
        let key = {state = current_state; symbol = tape.current} in
        let action = get_action key in
        print_endline (print_tape_and_state tape (key, action));
        let new_output = (print_tape_and_state tape (key, action)) :: output
          in 
        let next_tape =
          {tape with current = action.write} 
          |> shift_tape machine.blank action.move
        in
        compute action.next_state next_tape new_output
    in
    
    let starting_tape = match input with
      | [] -> { current = ""; left = []; right = [] }
      | hd::tl -> { current = hd; left = []; right = tl }
    in
    compute machine.initial starting_tape []