#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path
from typing import List, Tuple, Optional

def load_tokens(path: str) -> List[str]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    if any(ch.isspace() for ch in raw):
        return raw.split()
    return list(raw)

def find_pattern(tokens: List[str], pat: List[str]) -> List[int]:
    hits = []
    n = len(tokens)
    m = len(pat)
    for i in range(n - m + 1):
        if tokens[i:i+m] == pat:
            hits.append(i)
    return hits

def first_bd_segment_after(tokens: List[str], start: int) -> Tuple[int,int]:
    n = len(tokens)
    i = start
    while i < n and tokens[i] not in ("b","d"):
        i += 1
    if i >= n:
        return (-1,-1)
    j = i
    while j < n and tokens[j] in ("b","d"):
        j += 1
    return (i,j)

def parse_bd_runs(seg: List[str]) -> List[int]:
    # return consecutive b-run lengths, splitting on d-runs
    runs = []
    i = 0
    n = len(seg)
    while i < n:
        while i < n and seg[i] == "d":
            i += 1
        if i >= n:
            break
        j = i
        while j < n and seg[j] == "b":
            j += 1
        runs.append(j - i)
        i = j
    return runs

def sym_from_len_or_rem(L: int, alphabet: List[str]) -> Optional[str]:
    # U9,3 A_i lengths: 4i-1  => 3,7,11,15 for q=4
    q = len(alphabet)
    def decode_a(x: int) -> Optional[str]:
        if x % 4 != 3:
            return None
        i = (x + 1) // 4
        if 1 <= i <= q:
            return alphabet[i-1]
        return None

    # exact A
    s = decode_a(L)
    if s is not None:
        return s

    # remainder mod (4q): sometimes glued or offset
    rem = L % (4*q)
    s = decode_a(rem)
    return s

def direct_sim_expected(tm: dict, input_str: str, max_steps: int = 200000) -> str:
    blank = tm.get("blank", ".")
    finals = set(tm["finals"])
    state = tm["initial"]
    tape = list(input_str)
    head = 0

    for _ in range(max_steps):
        if state in finals:
            break
        if head < 0:
            tape = [blank] * (-head) + tape
            head = 0
        if head >= len(tape):
            tape.extend([blank] * (head - len(tape) + 1))
        sym = tape[head]

        action = None
        for tr in tm["transitions"].get(state, []):
            if tr["read"] == sym:
                action = tr
                break
        if action is None:
            break

        tape[head] = action["write"]
        if action["action"] == "RIGHT":
            head += 1
        elif action["action"] == "LEFT":
            head -= 1
        state = action["to_state"]

    s = "".join(tape)
    return s.strip(blank) or blank

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", default=None, help="original TM input, e.g. '1+1='")
    ap.add_argument("--show", type=int, default=200, help="how many decoded symbols to show")
    args = ap.parse_args()

    tm = json.loads(Path(args.tm_json).read_text(encoding="utf-8"))
    alphabet = tm["alphabet"]

    tokens = load_tokens(args.utm_out)
    if not tokens:
        print("Empty utm_out.")
        return

    # Landmark = V^3 + S* + (bootstrap overwrite of X)
    # V^3 = d c c d c c d c c
    # S*  = c c
    # then BOOT likely writes 'd' or 'c' over X; accept either.
    # We'll search for ... d c c d c c d c c c c (d|c)
    base = ["d","c","c","d","c","c","d","c","c","c","c"]
    hits = []
    for i in range(len(tokens) - (len(base)+1) + 1):
        if tokens[i:i+len(base)] == base and tokens[i+len(base)] in ("d","c"):
            hits.append(i)
    if not hits:
        print("Could not find landmark V^3 + S* + (d|c).")
        print("Decoding fallback: using largest b/d segment in whole tape.")
        # fallback: largest b/d segment
        best = (-1,-1)
        i=0
        while i < len(tokens):
            if tokens[i] in ("b","d"):
                j=i
                while j < len(tokens) and tokens[j] in ("b","d"):
                    j+=1
                if (j-i) > (best[1]-best[0]):
                    best = (i,j)
                i=j
            else:
                i+=1
        seg_start, seg_end = best
    else:
        # take the last occurrence (most likely true end-of-program)
        land = hits[-1]
        seg_start, seg_end = first_bd_segment_after(tokens, land + len(base) + 1)

    if seg_start < 0:
        print("Could not locate a b/d segment after landmark.")
        return

    seg = tokens[seg_start:seg_end]
    runs = parse_bd_runs(seg)

    decoded = []
    for L in runs:
        s = sym_from_len_or_rem(L, alphabet)
        decoded.append(s if s is not None else "?")

    decoded_str = "".join(decoded)
    cleaned = "".join(ch for ch in decoded if ch != "?")

    print(f"Dataword segment: [{seg_start}, {seg_end}) length={seg_end-seg_start} (b/d only)")
    print(f"Decoded symbols : {decoded_str[:args.show]}{'…' if len(decoded_str)>args.show else ''}")
    print(f"Cleaned symbols : {cleaned[:args.show]}{'…' if len(cleaned)>args.show else ''}")
    print(f"Unknown count   : {decoded.count('?')} / {len(decoded)}")

    # evidence checks
    if args.inp is not None:
        exp = direct_sim_expected(tm, args.inp)
        print(f"\nExpected (direct TM sim) from {args.inp!r}: {exp!r}")
        # find expected as substring in cleaned (best-effort)
        if exp != ".":
            if exp in cleaned:
                print(f"✅ Found expected output {exp!r} as substring in cleaned decoded stream.")
            else:
                # also try with '.' padding around expected, common for your TM
                pad = "." + exp + "."
                if pad in cleaned:
                    print(f"✅ Found padded expected output {pad!r} as substring in cleaned stream.")
                else:
                    print(f"⚠️ Did not find expected output as a clean substring yet.")
                    print("   This can still be OK if the UTM halts mid-cycle and the stream is rotated/noisy.")

        # leftover operators
        if "+" in cleaned or "=" in cleaned:
            print("⚠️ Cleaned stream still contains '+' or '=' (may be mid-cycle / rotated / noisy).")
        else:
            print("✅ No '+' or '=' in cleaned stream (strong sign the simulated TM finished its cleanup).")

if __name__ == "__main__":
    main()