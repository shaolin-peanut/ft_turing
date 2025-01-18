open Types

type tape = {
  current: string;
  left: string list;
  right: string list;
}

(** [halts] check if the symbol is a part of the halting symbols*)
let halts symbol finals =
  finals |> List.mem symbol

let tl_or_empty lst =
  match lst with
  | [] -> []
  | _ -> List.tl lst

let hd_or_blank blank = function
  | [] -> blank
  | hd :: _ -> hd

(** [shift_tape] shifts the tape according to the direction *)
let shift_tape blank direction tape =
  match direction with
  | Left -> {
        current = hd_or_blank blank tape.right;
        left = tape.current :: tape.left;
        right = tl_or_empty tape.right;
      }
  | Right -> {
    current = hd_or_blank blank tape.left;
    left = tl_or_empty tape.left;
    right = tape.current :: tape.right
    }

let print_tape_and_state tape (transition : transition) =
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
  let tape_str = left_str ^ tape.current ^ right_str in
  Printf.sprintf "%s\n%s" transition_str tape_str
    
  (** [run_machine] take the config of a turing machine,
  places the input string on the tape and runs the turing machine  *)
  let run_machine (machine : turing_machine) (input : string list) : string list =
    let get_action key =
      machine.transitions
      |> List.filter (fun (k, _) ->
        k.state = key.state && k.symbol = key.symbol)
      |> List.map snd 
      |> List.hd
    in
    
    let rec compute current_state (tape : tape) output =
      if halts tape.current machine.finals then
        List.rev output
      else
        let key = {state = current_state; symbol = tape.current} in
        let action = get_action key in
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