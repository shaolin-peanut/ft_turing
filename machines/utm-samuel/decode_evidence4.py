#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path
from typing import List, Tuple, Optional, Dict

def load_tokens(path: str) -> List[str]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    if any(ch.isspace() for ch in raw):
        return raw.split()
    return list(raw)

def find_landmark(tokens: List[str]) -> int:
    # V^3 + S* + (d|c) where V^3=dccdccdcc and S*=cc
    base = ["d","c","c","d","c","c","d","c","c","c","c"]
    last = -1
    for i in range(len(tokens) - (len(base)+1) + 1):
        if tokens[i:i+len(base)] == base and tokens[i+len(base)] in ("d","c"):
            last = i
    return last

def all_bd_segments(tokens: List[str], start: int = 0) -> List[Tuple[int,int]]:
    segs = []
    i = start
    n = len(tokens)
    while i < n:
        if tokens[i] in ("b","d"):
            j = i
            while j < n and tokens[j] in ("b","d"):
                j += 1
            segs.append((i,j))
            i = j
        else:
            i += 1
    return segs

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
        mv = action["action"]
        if mv == "RIGHT":
            head += 1
        elif mv == "LEFT":
            head -= 1
        state = action["to_state"]
    s = "".join(tape)
    return s.strip(blank) or blank

def gap_tolerant_regex(expected: str) -> re.Pattern:
    # Match e.g. "111" as "1[?]*1[?]*1" inside decoded stream
    # Allow '.' too if expected contains it (usually it doesn't).
    parts = []
    for ch in expected:
        parts.append(re.escape(ch))
    # allow any number of '?' between expected symbols
    pat = r"".join([p + r"\?*" for p in parts[:-1]] + [parts[-1]])
    return re.compile(pat)

def longest_ones_ignoring_q(decoded: str) -> int:
    # remove '?' and find max run of '1'
    s = decoded.replace("?", "")
    best = 0
    cur = 0
    for ch in s:
        if ch == "1":
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best

def score_segment(decoded: str, expected: Optional[str]) -> Tuple[int, Dict[str,int], Optional[Tuple[int,int]]]:
    """
    Higher is better.
    Penalize unknowns and operators.
    Reward expected match (gap tolerant).
    Reward long run of 1s (ignoring ?).
    """
    metrics = {
        "len": len(decoded),
        "unknown": decoded.count("?"),
        "plus": decoded.count("+"),
        "eq": decoded.count("="),
        "ones_run": longest_ones_ignoring_q(decoded),
    }

    score = 0
    score += metrics["len"] // 2
    score -= metrics["unknown"] * 5
    score -= (metrics["plus"] + metrics["eq"]) * 8
    score += metrics["ones_run"] * 6

    match_span = None
    if expected:
        rx = gap_tolerant_regex(expected)
        m = rx.search(decoded)
        if m:
            score += 500
            match_span = (m.start(), m.end())
        # also reward if expected appears in cleaned
        if expected in decoded.replace("?", ""):
            score += 250

    return score, metrics, match_span

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", default=None)
    ap.add_argument("--show", type=int, default=500)
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()

    tm = json.loads(Path(args.tm_json).read_text(encoding="utf-8"))
    alphabet = tm["alphabet"]
    tokens = load_tokens(args.utm_out)
    if not tokens:
        print("Empty utm_out.")
        return

    expected = direct_sim_expected(tm, args.inp) if args.inp else None
    if args.inp:
        print(f"Expected (direct TM sim) from {args.inp!r}: {expected!r}\n")

    land = find_landmark(tokens)
    start = land + 12 if land >= 0 else 0
    segs = all_bd_segments(tokens, start=start)
    if not segs:
        print("No b/d segments found.")
        return

    candidates = []
    for (a,b) in segs:
        seg = tokens[a:b]
        runs = parse_bd_runs(seg)
        if len(runs) < 10:
            continue
        decoded_syms = []
        for L in runs:
            s = sym_from_len_or_rem(L, alphabet)
            decoded_syms.append(s if s is not None else "?")
        decoded = "".join(decoded_syms)
        score, metrics, match_span = score_segment(decoded, expected if expected and expected != "." else None)
        candidates.append((score, a, b, decoded, metrics, match_span))

    if not candidates:
        print("No usable segments (too short after filtering).")
        return

    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]

    print("Best segment:")
    score, a, b, decoded, metrics, match_span = best
    print(f"  score={score}")
    print(f"  seg=[{a},{b}) len_syms={b-a} decoded_len={metrics['len']}")
    print(f"  unknown={metrics['unknown']} plus={metrics['plus']} eq={metrics['eq']} ones_run(ignoring ? )={metrics['ones_run']}")
    if match_span:
        print(f"  expected match span in decoded: {match_span}")
    print()
    print("Decoded (best):")
    out = decoded[:args.show] + ("…" if len(decoded) > args.show else "")
    print(out)
    print()
    print("Cleaned (best):")
    cleaned = decoded.replace("?", "")
    out2 = cleaned[:args.show] + ("…" if len(cleaned) > args.show else "")
    print(out2)

    print("\nTop segments:")
    for i, (score, a, b, decoded, metrics, match_span) in enumerate(candidates[:args.top], 1):
        tag = "MATCH" if match_span else ""
        print(f" {i:>2}. score={score:<5} seg=[{a},{b}) unk={metrics['unknown']:<3} +={metrics['plus']:<3} = {metrics['eq']:<3} ones_run={metrics['ones_run']:<3} {tag}")

if __name__ == "__main__":
    main()
