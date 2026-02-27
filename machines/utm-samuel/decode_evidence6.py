#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

U93_STATE_COUNT = 11


@dataclass
class RunLogEvidence:
    path: str
    checkpoints_raw: List[int]
    checkpoints_unique: List[int]
    max_checkpoint_m: Optional[int]
    crash_halt_seen: bool


@dataclass
class DirectSimEvidence:
    halted: bool
    crashed: bool
    steps: int
    final_state: str
    expected_output: str


@dataclass
class RunToken:
    run_idx: int
    seg_b_start: int
    seg_b_end: int
    seg_run_end: int
    b_len: int
    d_len_after: int
    kind: str
    state_idx: Optional[int]
    sym_idx: Optional[int]
    symbol: Optional[str]


@dataclass
class SegmentDecode:
    label: str
    seg_start: int
    seg_end: int
    run_count: int
    strict_count: int
    dropped_by_sep: int
    dropped_invalid: int
    strict_tokens: List[RunToken]


@dataclass
class Candidate:
    segment_label: str
    seg_start: int
    seg_end: int
    strict_start: int
    strict_end: int
    ea_run_idx: int
    ea_state_idx: int
    decoded: str
    trimmed: str
    operator_count: int
    raw_rel_start: int
    raw_rel_end: int


def project_to_expected_symbols(text: str, expected: str) -> str:
    allowed = set(expected)
    return "".join(ch for ch in text if ch in allowed)


@dataclass
class ParsedRun:
    run_idx: int
    b_start: int
    b_end: int
    d_end: int
    b_len: int
    d_len_after: int


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def load_tm(path: str) -> dict:
    return json.loads(read_text(path))


def load_tokens(path: str) -> List[str]:
    raw = read_text(path).strip()
    if not raw:
        return []
    if any(ch.isspace() for ch in raw):
        return raw.split()
    return list(raw)


def load_final_tape_tokens(path: str) -> Tuple[List[str], str]:
    raw = read_text(path)
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return ([], "empty")

    last_line_tokens = lines[-1].split()
    if len(last_line_tokens) >= 20 and all(len(tok) == 1 for tok in last_line_tokens):
        return (last_line_tokens, "last_line")

    tokens = load_tokens(path)
    return (tokens, "full_file")


def parse_run_log(path: str) -> RunLogEvidence:
    txt = read_text(path)
    cps = [int(m.group(1)) for m in re.finditer(r"\[Checkpoint @ (\d+)M steps\]", txt)]
    uniq = sorted(set(cps))
    max_cp = max(uniq) if uniq else None
    crash = ("Undefined transition (Crash Halt)" in txt) or ("[HALT]" in txt)
    return RunLogEvidence(
        path=path,
        checkpoints_raw=cps,
        checkpoints_unique=uniq,
        max_checkpoint_m=max_cp,
        crash_halt_seen=crash,
    )


def direct_simulate(tm: dict, input_str: str, max_steps: int) -> DirectSimEvidence:
    blank = tm.get("blank", ".")
    finals = set(tm["finals"])
    state = tm["initial"]
    tape = list(input_str)
    head = 0

    for step in range(max_steps):
        if state in finals:
            s = "".join(tape)
            return DirectSimEvidence(True, False, step, state, s.strip(blank) or blank)

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
            s = "".join(tape)
            return DirectSimEvidence(False, True, step, state, s.strip(blank) or blank)

        tape[head] = action["write"]
        if action["action"] == "RIGHT":
            head += 1
        elif action["action"] == "LEFT":
            head -= 1
        state = action["to_state"]

    s = "".join(tape)
    return DirectSimEvidence(False, False, max_steps, state, s.strip(blank) or blank)


def find_bd_segments(tokens: Sequence[str]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] in ("b", "d"):
            j = i
            while j < n and tokens[j] in ("b", "d"):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def largest_bd_segment(tokens: Sequence[str]) -> Tuple[int, int]:
    segs = find_bd_segments(tokens)
    if not segs:
        return (-1, -1)
    return max(segs, key=lambda ij: ij[1] - ij[0])


def find_landmark(tokens: Sequence[str]) -> int:
    base = ["d", "c", "c", "d", "c", "c", "d", "c", "c", "c", "c"]
    last = -1
    for i in range(len(tokens) - (len(base) + 1) + 1):
        if list(tokens[i : i + len(base)]) == base and tokens[i + len(base)] in ("d", "c"):
            last = i
    return last


def segment_after_landmark(tokens: Sequence[str], land: int) -> Tuple[int, int]:
    if land < 0:
        return (-1, -1)
    i = land + 12
    n = len(tokens)
    while i < n and tokens[i] != "b":
        i += 1
    if i >= n:
        return (-1, -1)
    j = i
    while j < n and tokens[j] in ("b", "d"):
        j += 1
    return (i, j)


def parse_bd_runs(seg: Sequence[str]) -> List[ParsedRun]:
    runs: List[ParsedRun] = []
    i = 0
    n = len(seg)
    run_idx = 0
    while i < n:
        while i < n and seg[i] == "d":
            i += 1
        if i >= n:
            break

        b_start = i
        j = i
        while j < n and seg[j] == "b":
            j += 1

        k = j
        while k < n and seg[k] == "d":
            k += 1

        runs.append(
            ParsedRun(
                run_idx=run_idx,
                b_start=b_start,
                b_end=j,
                d_end=k,
                b_len=j - b_start,
                d_len_after=k - j,
            )
        )
        run_idx += 1
        i = k

    return runs


def classify_exact_run_length(b_len: int, q: int) -> Tuple[str, Optional[int], Optional[int]]:
    if (b_len + 1) % 4 == 0:
        sym_idx = (b_len + 1) // 4
        if 1 <= sym_idx <= q:
            return ("A", None, sym_idx)

    for state_idx in range(1, U93_STATE_COUNT + 1):
        rem = b_len - (4 * q * state_idx)
        if (rem + 1) % 4 == 0:
            sym_idx = (rem + 1) // 4
            if 1 <= sym_idx <= q:
                return ("EA", state_idx, sym_idx)

    return ("INVALID", None, None)


def decode_segment_strict(seg_tokens: Sequence[str], alphabet: Sequence[str], label: str, seg_start: int, seg_end: int) -> SegmentDecode:
    q = len(alphabet)
    runs = parse_bd_runs(seg_tokens)

    strict_tokens: List[RunToken] = []
    dropped_by_sep = 0
    dropped_invalid = 0

    for run in runs:
        kind, state_idx, sym_idx = classify_exact_run_length(run.b_len, q)

        if run.d_len_after != 1:
            dropped_by_sep += 1
            continue
        if kind == "INVALID":
            dropped_invalid += 1
            continue

        symbol = alphabet[sym_idx - 1] if sym_idx is not None else None
        strict_tokens.append(
            RunToken(
                run_idx=run.run_idx,
                seg_b_start=run.b_start,
                seg_b_end=run.b_end,
                seg_run_end=run.d_end,
                b_len=run.b_len,
                d_len_after=run.d_len_after,
                kind=kind,
                state_idx=state_idx,
                sym_idx=sym_idx,
                symbol=symbol,
            )
        )

    return SegmentDecode(
        label=label,
        seg_start=seg_start,
        seg_end=seg_end,
        run_count=len(runs),
        strict_count=len(strict_tokens),
        dropped_by_sep=dropped_by_sep,
        dropped_invalid=dropped_invalid,
        strict_tokens=strict_tokens,
    )


def build_ea_candidates(seg: SegmentDecode, blank: str) -> List[Candidate]:
    tokens = seg.strict_tokens
    cands: List[Candidate] = []

    for ea_pos, tok in enumerate(tokens):
        if tok.kind != "EA" or tok.state_idx is None:
            continue

        best_by_output: Dict[str, Tuple[Tuple[int, int, int, int, str], Tuple[int, int, str, str, int]]] = {}

        for start in range(0, ea_pos + 1):
            for end in range(ea_pos + 1, len(tokens) + 1):
                window = tokens[start:end]
                ea_count = sum(1 for x in window if x.kind == "EA")
                if ea_count != 1:
                    continue

                decoded = "".join(x.symbol for x in window if x.symbol is not None)
                trimmed = decoded.strip(blank) or blank
                if not trimmed:
                    continue

                op_count = decoded.count("+") + decoded.count("=")
                key = (end - start, op_count, start, end, decoded)
                payload = (start, end, decoded, trimmed, op_count)
                prev = best_by_output.get(trimmed)
                if prev is None or key < prev[0]:
                    best_by_output[trimmed] = (key, payload)

        for _trimmed, (_key, payload) in best_by_output.items():
            start, end, decoded, trimmed, op_count = payload
            window = tokens[start:end]
            raw_rel_start = window[0].seg_b_start
            raw_rel_end = window[-1].seg_run_end
            cands.append(
                Candidate(
                    segment_label=seg.label,
                    seg_start=seg.seg_start,
                    seg_end=seg.seg_end,
                    strict_start=start,
                    strict_end=end,
                    ea_run_idx=tok.run_idx,
                    ea_state_idx=tok.state_idx,
                    decoded=decoded,
                    trimmed=trimmed,
                    operator_count=op_count,
                    raw_rel_start=raw_rel_start,
                    raw_rel_end=raw_rel_end,
                )
            )

    return cands


def choose_best_matching_candidate(matches: List[Candidate], target_state_count: int) -> Tuple[Optional[Candidate], bool]:
    if not matches:
        return (None, False)

    def key(c: Candidate) -> Tuple[int, int, int, int, int, int]:
        in_target = 0 if 1 <= c.ea_state_idx <= target_state_count else 1
        return (
            in_target,
            c.operator_count,
            c.strict_end - c.strict_start,
            c.seg_end - c.seg_start,
            c.ea_run_idx,
            c.ea_state_idx,
        )

    ranked = sorted(matches, key=key)
    best = ranked[0]

    if len(ranked) == 1:
        return (best, False)

    ambiguous = key(ranked[0]) == key(ranked[1])
    return (best, ambiguous)


def shorten(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3] + "..."


def render_raw_context(tokens: Sequence[str], abs_start: int, abs_end: int, context: int, max_chars: int) -> str:
    left = max(0, abs_start - context)
    right = min(len(tokens), abs_end + context)

    pre = " ".join(tokens[left:abs_start]).strip()
    mid = " ".join(tokens[abs_start:abs_end]).strip()
    post = " ".join(tokens[abs_end:right]).strip()

    content = f"... {pre} [ {mid} ] {post} ..."
    return shorten(content, max_chars)


def render_run_table(seg: SegmentDecode, cand: Candidate, table_radius: int, max_rows: int) -> List[str]:
    rows: List[str] = []
    strict = seg.strict_tokens
    if not strict:
        return rows

    lo = max(0, cand.strict_start - table_radius)
    hi = min(len(strict), cand.strict_end + table_radius)
    rows.append("    mark  sidx  run   b_len d_len kind state sym  seg[b_start:b_end) seg_run_end")

    produced = 0
    for sidx in range(lo, hi):
        tok = strict[sidx]
        in_window = cand.strict_start <= sidx < cand.strict_end
        is_head = tok.kind == "EA" and tok.run_idx == cand.ea_run_idx
        if is_head:
            mark = "H*"
        elif in_window:
            mark = " *"
        else:
            mark = "  "

        state_str = str(tok.state_idx) if tok.state_idx is not None else "-"
        sym_str = tok.symbol if tok.symbol is not None else "-"
        rows.append(
            f"    {mark:>2}   {sidx:>4} {tok.run_idx:>4} {tok.b_len:>7} {tok.d_len_after:>5} "
            f"{tok.kind:>4} {state_str:>5} {sym_str:>3}  "
            f"[{tok.seg_b_start}:{tok.seg_b_end}) {tok.seg_run_end}"
        )
        produced += 1
        if produced >= max_rows:
            rows.append("    ...")
            break

    return rows


def render_window_explainer(seg: SegmentDecode, cand: Candidate, radius: int) -> List[str]:
    rows: List[str] = []
    strict = seg.strict_tokens
    if not strict:
        return rows

    lo = max(0, cand.strict_start - radius)
    hi = min(len(strict), cand.strict_end + radius)

    left = "".join(tok.symbol or "?" for tok in strict[lo:cand.strict_start])
    mid = "".join(tok.symbol or "?" for tok in strict[cand.strict_start:cand.strict_end])
    right = "".join(tok.symbol or "?" for tok in strict[cand.strict_end:hi])

    rows.append("  Explain window      :")
    rows.append(f"    Decoded neighborhood : {left}[{mid}]{right}")
    rows.append("    Legend               : [ ] selected strict window, H marks head/state anchor (EA token)")
    rows.append("    Rows:")
    rows.append("      mark sidx run kind state sym  meaning")

    for sidx in range(lo, hi):
        tok = strict[sidx]
        in_window = cand.strict_start <= sidx < cand.strict_end
        is_head = tok.kind == "EA" and tok.run_idx == cand.ea_run_idx
        if is_head:
            mark = "H" if in_window else "h"
        elif in_window:
            mark = "*"
        else:
            mark = "."

        state_str = str(tok.state_idx) if tok.state_idx is not None else "-"
        sym_str = tok.symbol if tok.symbol is not None else "-"

        if tok.kind == "EA":
            meaning = f"anchor: head is on this symbol while machine is in state {state_str}"
        else:
            meaning = "ordinary decoded tape symbol"

        rows.append(
            f"      {mark:>4} {sidx:>4} {tok.run_idx:>3} {tok.kind:>4} {state_str:>5} {sym_str:>3}  {meaning}"
        )

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Strict U9,3 inverse decoder v6")
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", required=True)
    ap.add_argument("--run-log", dest="run_log", required=True)
    ap.add_argument("--show", type=int, default=300)
    ap.add_argument("--context", type=int, default=80, help="tokens of raw tape context around chosen window")
    ap.add_argument("--table", type=int, default=8, help="strict-run rows around chosen window")
    ap.add_argument("--explain-window", action="store_true", help="print a compact decoded neighborhood around the chosen strict window")
    ap.add_argument("--window-radius", type=int, default=6, help="strict tokens shown on each side for --explain-window")
    ap.add_argument("--strict", action="store_true", help="kept for CLI compatibility; v6 is strict by default")
    ap.add_argument("--max-steps", type=int, default=200000)
    args = ap.parse_args()

    reasons: List[str] = []

    tm = load_tm(args.tm_json)
    alphabet: List[str] = tm["alphabet"]
    blank: str = tm.get("blank", ".")
    target_state_count = len(tm["states"])

    direct = direct_simulate(tm, args.inp, args.max_steps)

    if not Path(args.run_log).exists():
        print("=== UTM Evidence Report v6 ===")
        print(f"Run log               : {args.run_log}")
        print("[FAIL] Missing run log; v6 requires run-log evidence for PASS.")
        return 1

    runlog = parse_run_log(args.run_log)

    tokens, token_mode = load_final_tape_tokens(args.utm_out)
    if not tokens:
        print("=== UTM Evidence Report v6 ===")
        print("[FAIL] Empty utm output artifact.")
        return 1

    segments: List[Tuple[str, Tuple[int, int]]] = []
    largest = largest_bd_segment(tokens)
    if largest[0] >= 0:
        segments.append(("largest_bd_segment", largest))

    land = find_landmark(tokens)
    after = segment_after_landmark(tokens, land)
    if after[0] >= 0:
        segments.append(("after_landmark", after))

    all_bd = sorted(find_bd_segments(tokens), key=lambda ij: ij[1] - ij[0], reverse=True)
    for idx, seg in enumerate(all_bd[:4], start=1):
        segments.append((f"top_bd_segment_{idx}", seg))

    dedup: Dict[Tuple[int, int], str] = {}
    for label, seg in segments:
        if seg not in dedup:
            dedup[seg] = label

    decoded_segments: List[SegmentDecode] = []
    all_candidates: List[Candidate] = []

    for (seg_start, seg_end), label in dedup.items():
        if seg_end <= seg_start:
            continue
        seg_tokens = tokens[seg_start:seg_end]
        decoded = decode_segment_strict(seg_tokens, alphabet, label, seg_start, seg_end)
        decoded_segments.append(decoded)
        all_candidates.extend(build_ea_candidates(decoded, blank))

    exact_matches = [c for c in all_candidates if c.trimmed == direct.expected_output]
    projected_matches = [
        c
        for c in all_candidates
        if project_to_expected_symbols(c.trimmed, direct.expected_output) == direct.expected_output
    ]

    best_exact, ambiguous_exact = choose_best_matching_candidate(exact_matches, target_state_count)
    best_projected, _ = choose_best_matching_candidate(projected_matches, target_state_count)
    segment_index = {(s.label, s.seg_start, s.seg_end): s for s in decoded_segments}

    print("=== UTM Evidence Report v6 ===")
    print(f"TM file               : {args.tm_json}")
    print(f"Input                 : {args.inp!r}")
    print(f"UTM output            : {args.utm_out}  (token source: {token_mode}, tokens={len(tokens)})")
    print(f"Run log               : {runlog.path}")
    print()

    print("[1] Run Evidence")
    cp_timeline = ", ".join(f"{x}M" for x in runlog.checkpoints_unique[:10])
    if len(runlog.checkpoints_unique) > 10:
        cp_timeline += ", ..."
    print(f"Checkpoint hits       : {len(runlog.checkpoints_raw)}")
    print(f"Checkpoint unique     : {runlog.checkpoints_unique}")
    if cp_timeline:
        print(f"Checkpoint timeline   : {cp_timeline}")
    print(f"Crash-halt marker     : {'YES' if runlog.crash_halt_seen else 'no'}")

    print()
    print("[2] Direct TM Ground Truth")
    print(f"Halts                 : {'YES' if direct.halted else 'no'}")
    print(f"Crash                 : {'YES' if direct.crashed else 'no'}")
    print(f"Steps                 : {direct.steps}")
    print(f"Final state           : {direct.final_state}")
    print(f"Expected output       : {direct.expected_output!r}")

    print()
    print("[3] Strict Decode Reconstruction")
    if not decoded_segments:
        print("No candidate b/d segments were decodable.")
    else:
        for seg in decoded_segments:
            print(
                f"- {seg.label}: [{seg.seg_start},{seg.seg_end}) runs={seg.run_count} strict={seg.strict_count} "
                f"drop_sep={seg.dropped_by_sep} drop_invalid={seg.dropped_invalid}"
            )

    print(f"Total EA candidates   : {len(all_candidates)}")
    print(f"Exact candidates      : {len(exact_matches)}")
    print(f"Projected candidates  : {len(projected_matches)}")

    shown = best_exact if best_exact is not None else best_projected
    showing_projected_only = (best_exact is None and best_projected is not None)

    if shown is not None:
        preview = shown.decoded[: args.show]
        if len(shown.decoded) > args.show:
            preview += "..."
        if showing_projected_only:
            print("Best projected-only diagnostic candidate:")
            print("  Note                : not eligible for PASS (exact match required).")
        else:
            print("Chosen exact candidate:")
        print(f"  Segment             : {shown.segment_label} [{shown.seg_start},{shown.seg_end})")
        print(f"  Strict window       : [{shown.strict_start},{shown.strict_end})")
        print(f"  Head run index      : {shown.ea_run_idx}")
        print(f"  Head state index    : {shown.ea_state_idx}")
        print(f"  Decoded window      : {preview}")
        print(f"  Trimmed output      : {shown.trimmed!r}")
        print(
            "  Projected output    : "
            f"{project_to_expected_symbols(shown.trimmed, direct.expected_output)!r}"
        )
        print(f"  Operators in window : {shown.operator_count}")

        seg_key = (shown.segment_label, shown.seg_start, shown.seg_end)
        chosen_seg = segment_index.get(seg_key)
        if chosen_seg is not None:
            abs_start = shown.seg_start + shown.raw_rel_start
            abs_end = shown.seg_start + shown.raw_rel_end
            print("  Raw token span      : "
                  f"[{abs_start},{abs_end}) (segment-relative [{shown.raw_rel_start},{shown.raw_rel_end}))")
            print("  Raw tape context    :")
            print("    " + render_raw_context(tokens, abs_start, abs_end, args.context, max_chars=1000))
            print("  Strict run table    :")
            for row in render_run_table(chosen_seg, shown, args.table, max_rows=64):
                print(row)
            print("  Strict legend       : '*'=selected window token, 'H*'=head/state anchor in selected window")
            if args.explain_window:
                for row in render_window_explainer(chosen_seg, shown, args.window_radius):
                    print(row)

    print()
    print("[4] Verdict")

    run_evidence_ok = True
    if not runlog.checkpoints_unique:
        run_evidence_ok = False
        reasons.append("no checkpoint markers in run log")
    elif (runlog.max_checkpoint_m or 0) < 1:
        run_evidence_ok = False
        reasons.append("max checkpoint below 1M")

    if runlog.crash_halt_seen:
        run_evidence_ok = False
        reasons.append("crash-halt marker present in run log")

    if not direct.halted:
        reasons.append("direct TM simulation did not halt")
    if direct.crashed:
        reasons.append("direct TM simulation crash-halted")

    if best_exact is None:
        reasons.append("no exact strict candidate matches expected output")
    if ambiguous_exact:
        reasons.append("ambiguous exact strict candidate ranking")

    passed = run_evidence_ok and direct.halted and (not direct.crashed) and (best_exact is not None) and (not ambiguous_exact)

    if passed:
        print("Verdict               : PASS")
        print("Summary               : Deterministic exact strict decode and run-log evidence both succeeded.")
        return 0

    print("Verdict               : FAIL")
    if reasons:
        print("Reasons               : " + "; ".join(reasons))
    else:
        print("Reasons               : strict proof conditions were not met")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
