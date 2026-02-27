#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from typing import List, Tuple, Optional

def load_tokens(path: str) -> List[str]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    if any(ch.isspace() for ch in raw):
        return raw.split()
    return list(raw)

def parse_bd_runs(seg: List[str]) -> List[int]:
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
    q = len(alphabet)
    def decode_a(x: int) -> Optional[str]:
        if x % 4 != 3:
            return None
        i = (x + 1) // 4
        return alphabet[i-1] if 1 <= i <= q else None

    s = decode_a(L)
    if s is not None:
        return s
    rem = L % (4*q)
    return decode_a(rem)

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

def find_landmark(tokens: List[str]) -> int:
    # V^3 + S* + (d|c)
    # V^3 = dcc dcc dcc, S* = cc
    base = ["d","c","c","d","c","c","d","c","c","c","c"]  # dccdccdcc + cc
    last = -1
    for i in range(len(tokens) - (len(base)+1) + 1):
        if tokens[i:i+len(base)] == base and tokens[i+len(base)] in ("d","c"):
            last = i
    return last

def dataword_segment_after_landmark(tokens: List[str], land: int) -> Tuple[int,int]:
    # Start at first 'b' AFTER landmark; then extend through contiguous b/d.
    # This avoids accidentally picking the single bootstrap 'd' chunk.
    if land < 0:
        return (-1,-1)
    start_search = land + 12  # base(11) + one more (d|c)
    i = start_search
    n = len(tokens)
    while i < n and tokens[i] != "b":
        i += 1
    if i >= n:
        return (-1,-1)
    j = i
    while j < n and tokens[j] in ("b","d"):
        j += 1
    return (i,j)

def largest_bd_segment(tokens: List[str]) -> Tuple[int,int]:
    best = (-1,-1)
    i=0
    n=len(tokens)
    while i<n:
        if tokens[i] in ("b","d"):
            j=i
            while j<n and tokens[j] in ("b","d"):
                j+=1
            if (j-i)>(best[1]-best[0]):
                best=(i,j)
            i=j
        else:
            i+=1
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", default=None)
    ap.add_argument("--show", type=int, default=300)
    args = ap.parse_args()

    tm = json.loads(Path(args.tm_json).read_text(encoding="utf-8"))
    alphabet = tm["alphabet"]

    tokens = load_tokens(args.utm_out)
    if not tokens:
        print("Empty utm_out.")
        return

    land = find_landmark(tokens)
    if land >= 0:
        seg_start, seg_end = dataword_segment_after_landmark(tokens, land)
    else:
        seg_start, seg_end = (-1,-1)

    if seg_start < 0:
        print("Could not locate dataword after landmark; falling back to largest b/d segment.")
        seg_start, seg_end = largest_bd_segment(tokens)

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

    if args.inp is not None:
        exp = direct_sim_expected(tm, args.inp)
        print(f"\nExpected (direct TM sim) from {args.inp!r}: {exp!r}")
        if exp != ".":
            if exp in cleaned:
                print(f"✅ Found expected output {exp!r} as substring in cleaned stream.")
            elif ("."+exp+".") in cleaned:
                print(f"✅ Found padded expected output {('.'+exp+'.')!r} in cleaned stream.")
            else:
                print("⚠️ Did not find expected output as a clean substring yet (could be rotated/noisy).")

        if "+" in cleaned or "=" in cleaned:
            print("⚠️ Cleaned stream still contains '+' or '='.")
        else:
            print("✅ No '+' or '=' in cleaned stream.")

if __name__ == "__main__":
    main()
