#!/usr/bin/env python3
import json
import sys

def encode_A(i):
    # Encoding for A symbol a_i is: ←−b repeated (4*i-3) times.
    # (We assume the interpreter already knows how to read the "←−b" marker.)
    return "←−b" * (4*i - 3)

def encode_E(j, g):
    # Encoding for E symbol e_j is: ←−b repeated (4*j*g) times.
    return "←−b" * (4 * j * g)

def encode_prod_EA(from_state_index, read_sym_index, write_sym_index, to_state_index, g):
    # For a production e_{from} a_{read} -> a_{write} e_{to},
    # the production encoding (per Equation (5)) is:
    #    〈P(eₓ aᵢ)〉 = "λ" + "d"^(4*to_state_index*g) + "dλ" + "d"^(4*write_sym_index - 3)
    part1 = "λ"
    part2 = "d" * (4 * to_state_index * g)
    part3 = "dλ"
    part4 = "d" * (4 * write_sym_index - 3)
    return part1 + part2 + part3 + part4

def encode_prod_A(a_index):
    # Identity production for a symbol: 〈P(aᵢ)〉 = "dλ" + "d"^(4*i-3)
    return "dλ" + "d" * (4 * a_index - 3)

def build_encoded_R(tm):
    states = tm["states"]
    symbols = tm["symbols"]
    transitions = tm["transitions"]

    # Let g be the number of tape symbols.
    g = len(symbols)
    # Let h be the number of states.
    h = len(states)
    
    # Build a lookup for transitions:
    # key: (from_state, read_symbol)  -> (write_symbol, to_state)
    trans_dict = {}
    for t in transitions:
    for name, value in transitions:
        key = (name, value["read"])
        trans_dict[key] = (value["write"], value["to_state"])

    print(trans_dict)
    
    # Build the production table for the BTS.
    # According to Equation (4) we need:
    # For each state e (except the halt state, which is the last state) in reverse order
    # and for each tape symbol in reverse order, output:
    #    "λ2" + 〈P(e a)〉
    prod_block = ""
    # We assume states are ordered and the last state is the halt state.
    # So we iterate for state indices 1 to (h-1), where index 1 corresponds to the first state.
    # We output in reverse order: state index (h-1) down to 1, and for each, symbol index g down to 1.
    for state_idx in range(h - 1, 0, -1):  # state index: h-1 ... 1
        state_name = states[state_idx - 1]
        for sym_idx in range(g, 0, -1):
            symbol = symbols[sym_idx - 1]
            key = (states[state_idx - 1], symbol)
            if key not in trans_dict:
                sys.exit(f"Error: no transition defined for state {states[state_idx - 1]} reading symbol {symbol}")
            write_sym, to_state = trans_dict[key]
            # Get indices:
            # from state index = state_idx
            # read symbol index = sym_idx
            # write symbol index: position of write_sym in symbols (1-indexed)
            try:
                write_sym_index = symbols.index(write_sym) + 1
            except ValueError:
                sys.exit(f"Error: write symbol {write_sym} not found in symbols list")
            # to state index: position of to_state in states (1-indexed)
            try:
                to_state_index = states.index(to_state) + 1
            except ValueError:
                sys.exit(f"Error: to state {to_state} not found in states list")
            prod_encoding = encode_prod_EA(state_idx, sym_idx, write_sym_index, to_state_index, g)
            prod_block += "λ2" + prod_encoding
    # Now, add the identity productions for each tape symbol.
    id_block = ""
    for sym_idx in range(g, 0, -1):
        id_encoding = encode_prod_A(sym_idx)
        id_block += "λ3" + id_encoding

    # Prepend the header markers: "−→b" followed by "c"
    header = "−→b" + "c"
    
    encoded_R = header + prod_block + id_block
    return encoded_R

def main():
    if len(sys.argv) < 2:
        print("Usage: python encoder.py <tm_description.json>")
        sys.exit(1)
    
    filename = sys.argv[1]
    with open(filename, "r") as f:
        tm = json.load(f)
    
    encoded = build_encoded_R(tm)
    print(encoded)

if __name__ == '__main__':
    main()

