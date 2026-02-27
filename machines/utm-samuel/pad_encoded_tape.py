#!/usr/bin/env python3
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: pad_encoded_tape.py <N_blanks>", file=sys.stderr)
        sys.exit(2)

    N = int(sys.argv[1])
    tape = sys.stdin.read().strip()
    toks = tape.split()
    if len(toks) < 3:
        print(tape)
        return

    # Find the last occurrence of "... c c c" (terminator used in your encodings)
    # We'll insert before it.
    idx = -1
    for i in range(len(toks) - 3, -1, -1):
        if toks[i:i+3] == ["c", "c", "c"]:
            idx = i
            break

    if idx == -1:
        # No terminator found; just append (better than nothing)
        idx = len(toks)

    # blank '.' is A_2 => b^(4*2-1)=b^7, and symbols are delimited by 'd'
    blank_cell = ["b"] * 7 + ["d"]

    inject = blank_cell * N
    new_toks = toks[:idx] + inject + toks[idx:]

    print(" ".join(new_toks))

if __name__ == "__main__":
    main()
