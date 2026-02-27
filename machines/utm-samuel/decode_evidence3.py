#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from typing import List, Tuple, Optional

# ----------------------------
# I/O + basic parsing
# ----------------------------

def load_tokens(path: str) -> List[str]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    if any(ch.isspace() for ch in raw):
        return raw.split()
    return list(raw)

def parse_bd_runs(seg: List[str]) -> List[int]:
    """Return lengths of consecutive b-runs, splitting on d."""
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

# ----------------------------
# Neary–Woods decoding heuristics
# ----------------------------

def sym_from_len_or_rem(L: int, alphabet: List[str]) -> Optional[str]:
    """
    U9,3 tape symbol encoding: A_i = b^(4i-1).
    We decode either exact length, or remainder modulo 4q (useful if glued/offset).
    """
    q = len(alphabet)

    def decode_a(x: int) -> Optional[str]:
        if x % 4 != 3:
            return None
        i = (x + 1) // 4
        return alphabet[i-1] if 1 <= i <= q else None

    s = decode_a(L)
    if s is not None:
        return s
    rem = L % (4 * q)
    return decode_a(rem)

def find_landmark(tokens: List[str]) -> int:
    """
    Find last occurrence of: V^3 + S* + (d|c)
    V^3 = dcc dcc dcc
    S*  = cc
    then bootstrap overwrites X with d or c (we accept either).
    """
    base = ["d","c","c","d","c","c","d","c","c","c","c"]  # dccdccdcc + cc
    last = -1
    for i in range(len(tokens) - (len(base)+1) + 1):
        if tokens[i:i+len(base)] == base and tokens[i+len(base)] in ("d","c"):
            last = i
    return last

def dataword_segment_after_landmark(tokens: List[str], land: int) -> Tuple[int,int]:
    """
    Start at first 'b' after landmark, then extend while (b|d).
    This avoids choosing a single bootstrap 'd' as the segment.
    """
    if land < 0:
        return (-1, -1)
    start_search = land + 12  # base(11) + one (d|c)
    i = start_search
    n = len(tokens)
    while i < n and tokens[i] != "b":
        i += 1
    if i >= n:
        return (-1, -1)
    j = i
    while j < n and tokens[j] in ("b", "d"):
        j += 1
    return (i, j)

def largest_bd_segment(tokens: List[str]) -> Tuple[int,int]:
    best = (-1, -1)
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] in ("b", "d"):
            j = i
            while j < n and tokens[j] in ("b", "d"):
                j += 1
            if (j - i) > (best[1] - best[0]):
                best = (i, j)
            i = j
        else:
            i += 1
    return best

# ----------------------------
# Direct simulation of target TM (for expected output)
# ----------------------------

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
        mv = action["action"]
        if mv == "RIGHT":
            head += 1
        elif mv == "LEFT":
            head -= 1
        state = action["to_state"]

    s = "".join(tape)
    return s.strip(blank) or blank

# ----------------------------
# Output-block extraction
# ----------------------------

def extract_pure_blocks(decoded: List[str], allowed=set([".", "1"])) -> List[Tuple[int,int,str]]:
    """
    Extract contiguous blocks consisting only of allowed symbols (no '?', no '+', no '=').
    Returns list of (start_idx, end_idx_exclusive, block_string).
    """
    blocks = []
    i = 0
    n = len(decoded)
    while i < n:
        if decoded[i] in allowed:
            j = i
            while j < n and decoded[j] in allowed:
                j += 1
            blocks.append((i, j, "".join(decoded[i:j])))
            i = j
        else:
            i += 1
    return blocks

def best_blocks_report(blocks: List[Tuple[int,int,str]], top_n: int = 8) -> List[Tuple[int,int,str,int]]:
    scored = [(a,b,s,len(s)) for (a,b,s) in blocks]
    scored.sort(key=lambda x: x[3], reverse=True)
    return scored[:top_n]

# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", default=None, help="original TM input, e.g. '11+1='")
    ap.add_argument("--show", type=int, default=400, help="how many decoded symbols to print")
    ap.add_argument("--top", type=int, default=8, help="how many pure blocks to list")
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
        seg_start, seg_end = (-1, -1)

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
    print()

    # Evidence: operator leftovers anywhere in cleaned stream
    has_plus = "+" in cleaned
    has_eq = "=" in cleaned
    print(f"Operators in cleaned stream: '+'={'YES' if has_plus else 'no'}  '={'YES' if has_eq else 'no'}")
    print()

    # Extract pure blocks of only '.' and '1' (good candidates for final tape content)
    pure_blocks = extract_pure_blocks(decoded, allowed=set([".", "1"]))
    top_blocks = best_blocks_report(pure_blocks, top_n=args.top)

    if not top_blocks:
        print("No pure blocks of only {'.','1'} found. (Likely decoding too noisy or wrong segment.)")
    else:
        print(f"Top {len(top_blocks)} pure blocks of only '.' and '1' (best candidates for final result):")
        for rank, (a, b, s, L) in enumerate(top_blocks, start=1):
            preview = s if len(s) <= 80 else (s[:77] + "…")
            print(f" {rank:>2}. idx[{a}:{b}] len={L:<4}  {preview}")
        print()

    # Expected output check
    if args.inp is not None:
        exp = direct_sim_expected(tm, args.inp)
        print(f"Expected (direct TM sim) from {args.inp!r}: {exp!r}")

        # stronger validation: find a pure block that contains exp and has same count of '1'
        exp_ones = exp.count("1")
        found_strong = False

        for (a, b, s, L) in top_blocks:
            if exp in s or ("." + exp + ".") in s:
                # also check ones count roughly matches
                if s.count("1") >= exp_ones:
                    found_strong = True
                    print(f"✅ Found expected output inside a PURE block: idx[{a}:{b}] len={L}, ones={s.count('1')}")
                    # show a focused snippet around the match
                    m = s.find(exp)
                    if m == -1:
                        m = s.find("." + exp + ".")
                        match_len = len("." + exp + ".")
                    else:
                        match_len = len(exp)
                    lo = max(0, m - 20)
                    hi = min(len(s), m + match_len + 20)
                    print("   Context:", s[lo:hi])
                    break

        if not found_strong:
            print("⚠️ Did not find expected output inside a PURE {'.','1'} block.")
            print("   (You might still see it in the cleaned stream, but the clean final tape slice isn't isolated yet.)")

        # extra: if you *expect* no '+'/'=' at true halt
        if has_plus or has_eq:
            print("⚠️ '+' or '=' still appear somewhere in cleaned stream.")
            print("   This usually means: you're decoding a superset of the current configuration, or the UTM halted mid-cycle.")
        else:
            print("✅ No '+' or '=' anywhere in cleaned stream (stronger sign of clean halt).")

if __name__ == "__main__":
    main()