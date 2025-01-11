type name = string

type transition = {
  read: string;
  to_state: string;
  write: string;
  direction: string;
}

type turing_machine = {
  name: name;
  alphabet: string list;
  blank: string;
  states: string list;
}