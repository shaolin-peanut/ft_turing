#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# ----------------------------
# Helpers
# ----------------------------

def load_tape(path: str) -> List[str]:
    raw = Path(path).read_text(encoding="utf-8", errors="ignore").strip()
    if not raw:
        return []
    # Most ft_turing dumps are space-separated symbols
    if any(ch.isspace() for ch in raw):
        return raw.split()
    # Fallback: treat as raw characters
    return list(raw)

def find_bd_segments(tape: List[str]) -> List[Tuple[int, int]]:
    segs = []
    i = 0
    n = len(tape)
    while i < n:
        if tape[i] in ("b", "d"):
            j = i
            while j < n and tape[j] in ("b", "d"):
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    return segs

def parse_bd_runs(seg: List[str]) -> List[Tuple[int, int]]:
    """
    Return list of (b_len, d_len_after) for consecutive b-blocks separated by some d's.
    """
    runs = []
    i = 0
    n = len(seg)
    while i < n:
        # skip d's
        while i < n and seg[i] == "d":
            i += 1
        if i >= n:
            break
        j = i
        while j < n and seg[j] == "b":
            j += 1
        b_len = j - i
        k = j
        while k < n and seg[k] == "d":
            k += 1
        d_len = k - j
        runs.append((b_len, d_len))
        i = k
    return runs

def simulate_tm_expected(tm: dict, input_str: str, max_steps: int = 200000) -> str:
    blank = tm.get("blank", ".")
    transitions = tm["transitions"]
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
        for tr in transitions.get(state, []):
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

    # Trim noisy blanks at both ends for display
    s = "".join(tape)
    return s.strip(blank) or blank

# ----------------------------
# Decoding logic
# ----------------------------

def build_maps(alphabet: List[str], states: List[str]) -> Tuple[Dict[int, str], Dict[int, Tuple[str, str, str]]]:
    """
    A blocks (strict): b^(4*i - 1) for i=1..q
    Head block (strict): b^(4*q*j + (4*i - 1))
      - We will try two interpretations for j:
        (A) state-only: j in 1..|states|
        (B) state×readSymbol: j in 1..|states|*q, decoded as:
            state_idx = (j-1)//q, read_sym_idx=(j-1)%q
    We store head_len -> (stateName, readSym, gluedASym)
    """
    q = len(alphabet)
    A_len_to_sym = {4 * (i + 1) - 1: alphabet[i] for i in range(q)}

    head_len_to_info = {}

    # (A) state-only
    for j in range(1, len(states) + 1):
        for i in range(1, q + 1):
            L = 4 * q * j + (4 * i - 1)
            head_len_to_info[L] = (states[j - 1], "?", alphabet[i - 1])

    # (B) state×readSymbol
    for j in range(1, len(states) * q + 1):
        state_idx = (j - 1) // q
        read_idx = (j - 1) % q
        for i in range(1, q + 1):
            L = 4 * q * j + (4 * i - 1)
            head_len_to_info[L] = (states[state_idx], alphabet[read_idx], alphabet[i - 1])

    return A_len_to_sym, head_len_to_info

def loose_symbol_from_len(b_len: int, q: int, alphabet: List[str]) -> Optional[str]:
    """
    If b_len isn't an exact A block, try decoding by remainder mod (4*q):
      b_len % (4*q) == (4*i-1)  => suggests glued prefix + A_i
    """
    mod = 4 * q
    rem = b_len % mod
    for i in range(1, q + 1):
        if rem == (4 * i - 1):
            return alphabet[i - 1]
    return None

def score_candidate(runs: List[Tuple[int, int]],
                    A_len_to_sym: Dict[int, str],
                    head_len_to_info: Dict[int, Tuple[str, str, str]],
                    head_idx: int,
                    loose: bool,
                    alphabet: List[str]) -> Tuple[int, List[str], Tuple[str, str, str]]:
    q = len(alphabet)
    decoded: List[str] = []
    score = 0
    head_info = ("?", "?", "?")

    for idx, (b_len, d_len) in enumerate(runs):
        if idx == head_idx and b_len in head_len_to_info:
            st, read, glued = head_len_to_info[b_len]
            head_info = (st, read, glued)
            decoded.append(f"[{glued}]")
            score += 80
        else:
            sym = A_len_to_sym.get(b_len)
            if sym is None and loose:
                sym = loose_symbol_from_len(b_len, q, alphabet)
            if sym is None:
                decoded.append("?")
                score -= 10
            else:
                decoded.append(sym)
                score += 6

        # separator “quality”
        if d_len == 1:
            score += 2
        elif d_len == 0:
            score -= 1
        else:
            score -= (d_len - 1)

    # extra penalty for lots of unknowns
    score -= decoded.count("?") * 3
    return score, decoded, head_info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--loose", action="store_true", help="also decode by remainder when exact lengths don't match")
    ap.add_argument("--expect-input", type=str, default=None, help="e.g. '111+11=' (prints expected TM result)")
    args = ap.parse_args()

    tm = json.loads(Path(args.tm_json).read_text(encoding="utf-8"))
    alphabet = tm["alphabet"]
    states = tm["states"]

    tape = load_tape(args.utm_out)
    if not tape:
        print("Empty tape.")
        return

    segs = find_bd_segments(tape)
    if not segs:
        print("No {b,d}-only segment found in tape. This decoder expects a b/d dataword encoding.")
        return

    # pick the largest segment
    seg_start, seg_end = max(segs, key=lambda ij: ij[1] - ij[0])
    seg = tape[seg_start:seg_end]
    runs = parse_bd_runs(seg)

    A_len_to_sym, head_len_to_info = build_maps(alphabet, states)

    # candidate head positions
    candidates = []
    for head_idx, (b_len, _d_len) in enumerate(runs):
        if b_len in head_len_to_info:
            score, decoded, head_info = score_candidate(
                runs, A_len_to_sym, head_len_to_info, head_idx, args.loose, alphabet
            )
            candidates.append((score, head_idx, head_info, decoded))

    if not candidates:
        print("No head candidate matched strict head-length formula.")
        print("Try --loose, or the tape is not in a clean decodable form at halt.")
        return

    candidates.sort(key=lambda x: x[0], reverse=True)

    if args.expect_input is not None:
        expected = simulate_tm_expected(tm, args.expect_input)
        print(f"Expected (direct TM sim) from input {args.expect_input!r}: {expected!r}\n")

    print(f"Best candidate (highest score):")
    best = candidates[0]
    score, head_idx, (st, read, glued), decoded = best
    print(f"  Score           : {score}")
    print(f"  Tape segment    : [{seg_start}, {seg_end}) (length {seg_end-seg_start} symbols)")
    print(f"  Decoded state   : {st}")
    print(f"  Read symbol (if state×sym encoding): {read}")
    print(f"  Head at run idx : {head_idx}")
    w = args.window
    lo = max(0, head_idx - w)
    hi = min(len(decoded), head_idx + w + 1)
    snippet = "".join(decoded[lo:hi])
    print(f"  Window          : {snippet}\n")

    # Unknown summary
    unk = decoded.count("?")
    if unk:
        print(f"⚠️  Decoded word contains {unk} unknown blocks ('?').")
        print("    If this stays high, it usually means the UTM halted mid-cycle or the tape region isn't a clean dataword.\n")

    print(f"Top {min(args.top, len(candidates))} candidates:")
    for rank, (score, head_idx, (st, read, glued), decoded) in enumerate(candidates[: args.top], start=1):
        lo = max(0, head_idx - 20)
        hi = min(len(decoded), head_idx + 21)
        snippet = "".join(decoded[lo:hi])
        print(f" {rank:>2}. score={score:>5} head={head_idx:<4} state={st:<8} read={read:<2}  {snippet}")

if __name__ == "__main__":
    main()
