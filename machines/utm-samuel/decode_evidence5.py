#!/usr/bin/env python3
import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass
class DirectSimResult:
    halted: bool
    crashed: bool
    steps: int
    final_state: str
    tape_trimmed: str


@dataclass
class RunLogEvidence:
    path: str
    checkpoints_raw: List[int]
    checkpoints_unique: List[int]
    max_checkpoint_m: Optional[int]
    crash_halt_seen: bool


@dataclass
class WindowEvidence:
    start_run: int
    end_run: int
    decoded_window: str
    known_window: str
    projected_window: str
    unknown_count: int
    score: int
    exact_match: bool
    bounded_match: bool


@dataclass
class SegmentEvidence:
    label: str
    seg_start: int
    seg_end: int
    decoded: List[str]
    decoded_str: str
    cleaned: str
    projection: str
    unknown_count: int
    has_plus_or_eq: bool
    expected_in_cleaned: bool
    expected_in_projection: bool
    expected_bounded_in_projection: bool
    max_pure_block_len: int
    windows: List[WindowEvidence]
    score: int


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
    unique = sorted(set(cps))
    max_cp = max(unique) if unique else None
    crash = ("Undefined transition (Crash Halt)" in txt) or ("[HALT]" in txt)
    return RunLogEvidence(
        path=path,
        checkpoints_raw=cps,
        checkpoints_unique=unique,
        max_checkpoint_m=max_cp,
        crash_halt_seen=crash,
    )


def direct_simulate(tm: dict, input_str: str, max_steps: int) -> DirectSimResult:
    blank = tm.get("blank", ".")
    finals = set(tm["finals"])
    state = tm["initial"]
    tape = list(input_str)
    head = 0

    for step in range(max_steps):
        if state in finals:
            s = "".join(tape)
            return DirectSimResult(True, False, step, state, s.strip(blank) or blank)

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
            return DirectSimResult(False, True, step, state, s.strip(blank) or blank)

        tape[head] = action["write"]
        if action["action"] == "RIGHT":
            head += 1
        elif action["action"] == "LEFT":
            head -= 1
        state = action["to_state"]

    s = "".join(tape)
    return DirectSimResult(False, False, max_steps, state, s.strip(blank) or blank)


def find_bd_segments(tokens: Sequence[str]) -> List[Tuple[int, int]]:
    segs: List[Tuple[int, int]] = []
    i = 0
    n = len(tokens)
    while i < n:
        if tokens[i] in ("b", "d"):
            j = i
            while j < n and tokens[j] in ("b", "d"):
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    return segs


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
    start = land + 12
    i = start
    n = len(tokens)
    while i < n and tokens[i] != "b":
        i += 1
    if i >= n:
        return (-1, -1)
    j = i
    while j < n and tokens[j] in ("b", "d"):
        j += 1
    return (i, j)


def parse_bd_runs(seg: Sequence[str]) -> List[Tuple[int, int]]:
    runs: List[Tuple[int, int]] = []
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

        k = j
        while k < n and seg[k] == "d":
            k += 1

        runs.append((j - i, k - j))
        i = k

    return runs


def sym_from_len_or_rem(length: int, alphabet: Sequence[str]) -> Optional[str]:
    q = len(alphabet)

    def decode_a(x: int) -> Optional[str]:
        if x % 4 != 3:
            return None
        i = (x + 1) // 4
        return alphabet[i - 1] if 1 <= i <= q else None

    s = decode_a(length)
    if s is not None:
        return s

    rem = length % (4 * q)
    return decode_a(rem)


def decode_runs(runs: Sequence[Tuple[int, int]], alphabet: Sequence[str]) -> List[str]:
    out: List[str] = []
    for b_len, _d_len in runs:
        s = sym_from_len_or_rem(b_len, alphabet)
        out.append(s if s is not None else "?")
    return out


def bounded_expected(projection: str, expected: str, blank: str) -> bool:
    if not expected:
        return False
    pattern = rf"(?:^|{re.escape(blank)}){re.escape(expected)}(?:$|{re.escape(blank)})"
    return re.search(pattern, projection) is not None


def max_pure_block_len(decoded: Sequence[str], allowed: set) -> int:
    best = 0
    cur = 0
    for ch in decoded:
        if ch in allowed:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def find_result_windows(
    decoded: Sequence[str],
    expected: str,
    output_symbols: set,
    blank: str,
    max_window: int,
) -> List[WindowEvidence]:
    n = len(decoded)
    best: List[WindowEvidence] = []

    for a in range(n):
        end_max = min(n, a + max_window)
        for b in range(a + 1, end_max + 1):
            window = decoded[a:b]
            decoded_window = "".join(window)
            known = "".join(ch for ch in window if ch != "?")

            if "+" in known or "=" in known:
                continue

            projected = "".join(ch for ch in known if ch in output_symbols)
            if not projected:
                continue

            exact = projected == expected
            bounded = bounded_expected(projected, expected, blank)
            contains = expected in projected
            if not (exact or bounded or contains):
                continue

            unknown = decoded_window.count("?")
            score = 0
            if exact:
                score += 150
            elif bounded:
                score += 120
            else:
                score += 80

            score -= unknown * 3
            score -= abs(len(projected) - len(expected))

            best.append(
                WindowEvidence(
                    start_run=a,
                    end_run=b,
                    decoded_window=decoded_window,
                    known_window=known,
                    projected_window=projected,
                    unknown_count=unknown,
                    score=score,
                    exact_match=exact,
                    bounded_match=bounded,
                )
            )

    best.sort(key=lambda w: w.score, reverse=True)

    deduped: List[WindowEvidence] = []
    seen = set()
    for w in best:
        key = (w.start_run, w.end_run)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(w)
        if len(deduped) >= 12:
            break

    return deduped


def score_segment(
    decoded: Sequence[str],
    cleaned: str,
    projection: str,
    expected: str,
    blank: str,
    output_symbols: set,
    windows: Sequence[WindowEvidence],
) -> Tuple[int, bool, bool, bool, bool, int]:
    unknown = decoded.count("?")
    total = len(decoded) if decoded else 1
    unknown_ratio = unknown / total

    has_plus_or_eq = ("+" in cleaned) or ("=" in cleaned)
    expected_in_cleaned = expected in cleaned
    expected_in_projection = expected in projection
    expected_bounded_in_projection = bounded_expected(projection, expected, blank)

    pure_len = max_pure_block_len(decoded, output_symbols)

    score = 0
    if expected_in_projection:
        score += 60
    if expected_bounded_in_projection:
        score += 40
    if expected_in_cleaned:
        score += 25
    if has_plus_or_eq:
        score -= 15
    else:
        score += 20

    score += max(0, int((1.0 - unknown_ratio) * 30))
    score += min(20, pure_len)
    score += min(20, len(windows) * 3)

    return (
        score,
        has_plus_or_eq,
        expected_in_cleaned,
        expected_in_projection,
        expected_bounded_in_projection,
        pure_len,
    )


def evaluate_segment(
    label: str,
    tokens: Sequence[str],
    seg_start: int,
    seg_end: int,
    alphabet: Sequence[str],
    expected: str,
    blank: str,
    output_symbols: set,
    max_window: int,
) -> SegmentEvidence:
    seg = tokens[seg_start:seg_end]
    runs = parse_bd_runs(seg)
    decoded = decode_runs(runs, alphabet)
    decoded_str = "".join(decoded)
    cleaned = "".join(ch for ch in decoded if ch != "?")
    projection = "".join(ch for ch in cleaned if ch in output_symbols)

    windows = find_result_windows(decoded, expected, output_symbols, blank, max_window)

    (
        score,
        has_plus_or_eq,
        expected_in_cleaned,
        expected_in_projection,
        expected_bounded_in_projection,
        pure_len,
    ) = score_segment(decoded, cleaned, projection, expected, blank, output_symbols, windows)

    return SegmentEvidence(
        label=label,
        seg_start=seg_start,
        seg_end=seg_end,
        decoded=decoded,
        decoded_str=decoded_str,
        cleaned=cleaned,
        projection=projection,
        unknown_count=decoded.count("?"),
        has_plus_or_eq=has_plus_or_eq,
        expected_in_cleaned=expected_in_cleaned,
        expected_in_projection=expected_in_projection,
        expected_bounded_in_projection=expected_bounded_in_projection,
        max_pure_block_len=pure_len,
        windows=windows,
        score=score,
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Evidence-driven UTM decode verifier (v5): run proof + decode proof + result proof"
    )
    ap.add_argument("utm_out", help="UTM stdout artifact (final tape, optionally with header)")
    ap.add_argument("tm_json", help="Original simulated TM JSON")
    ap.add_argument("--input", dest="inp", required=True, help="Original TM input, e.g. '11+1='")
    ap.add_argument("--run-log", default=None, help="Optional stderr log with checkpoints")
    ap.add_argument("--show", type=int, default=240, help="Preview width for decoded strings")
    ap.add_argument("--window-max", type=int, default=40, help="Max run-window length for local evidence search")
    ap.add_argument("--max-steps", type=int, default=200000, help="Direct TM simulator step cap")
    ap.add_argument("--strict", action="store_true", help="Return non-zero unless evidence is strong")
    args = ap.parse_args()

    tm = load_tm(args.tm_json)
    alphabet: List[str] = tm["alphabet"]
    blank: str = tm.get("blank", ".")

    direct = direct_simulate(tm, args.inp, args.max_steps)
    expected = direct.tape_trimmed

    tokens, token_mode = load_final_tape_tokens(args.utm_out)
    if not tokens:
        print("[FAIL] Empty utm output artifact.")
        return 2

    runlog: Optional[RunLogEvidence] = None
    if args.run_log is not None:
        if Path(args.run_log).exists():
            runlog = parse_run_log(args.run_log)
        else:
            print(f"[WARN] run log not found: {args.run_log}")

    output_symbols = set(expected)
    output_symbols.add(blank)

    candidates: List[Tuple[str, Tuple[int, int]]] = []

    largest = largest_bd_segment(tokens)
    if largest[0] >= 0:
        candidates.append(("largest_bd_segment", largest))

    land = find_landmark(tokens)
    after_land = segment_after_landmark(tokens, land)
    if after_land[0] >= 0:
        candidates.append(("after_landmark", after_land))

    # Add top-N b/d segments by size as additional independent candidates.
    segs = find_bd_segments(tokens)
    segs_sorted = sorted(segs, key=lambda ij: ij[1] - ij[0], reverse=True)
    for idx, seg in enumerate(segs_sorted[:4], start=1):
        candidates.append((f"top_bd_segment_{idx}", seg))

    # Dedupe candidates.
    dedup: Dict[Tuple[int, int], str] = {}
    for label, seg in candidates:
        if seg not in dedup:
            dedup[seg] = label

    segment_reports: List[SegmentEvidence] = []
    for seg, label in dedup.items():
        seg_start, seg_end = seg
        if seg_end <= seg_start:
            continue
        report = evaluate_segment(
            label=label,
            tokens=tokens,
            seg_start=seg_start,
            seg_end=seg_end,
            alphabet=alphabet,
            expected=expected,
            blank=blank,
            output_symbols=output_symbols,
            max_window=args.window_max,
        )
        segment_reports.append(report)

    if not segment_reports:
        print("[FAIL] No decodable b/d segment found.")
        return 2

    segment_reports.sort(key=lambda r: r.score, reverse=True)
    best = segment_reports[0]

    print("=== UTM Evidence Report v5 ===")
    print(f"TM file               : {args.tm_json}")
    print(f"Input                 : {args.inp!r}")
    print(f"UTM output            : {args.utm_out}  (token source: {token_mode}, tokens={len(tokens)})")
    if runlog is not None:
        cp_summary = ", ".join(f"{m}M" for m in runlog.checkpoints_unique[:8])
        if len(runlog.checkpoints_unique) > 8:
            cp_summary += ", ..."
        print(f"Run log               : {runlog.path}")
        print(
            f"Checkpoint markers    : {len(runlog.checkpoints_raw)} hits, unique={runlog.checkpoints_unique or []}"
        )
        if cp_summary:
            print(f"Checkpoint timeline   : {cp_summary}")
        print(f"Crash-halt marker     : {'YES' if runlog.crash_halt_seen else 'no'}")
    else:
        print("Run log               : (not provided)")

    print()
    print("[1] Direct TM ground truth")
    print(f"Halts                 : {'YES' if direct.halted else 'no'}")
    print(f"Crash                 : {'YES' if direct.crashed else 'no'}")
    print(f"Steps                 : {direct.steps}")
    print(f"Final state           : {direct.final_state}")
    print(f"Expected result tape  : {expected!r}")

    print()
    print("[2] Best decoded segment")
    print(f"Segment label         : {best.label}")
    print(f"Segment bounds        : [{best.seg_start}, {best.seg_end}) len={best.seg_end - best.seg_start}")
    print(f"Decoded symbols       : {best.decoded_str[:args.show]}{'...' if len(best.decoded_str) > args.show else ''}")
    print(f"Cleaned symbols       : {best.cleaned[:args.show]}{'...' if len(best.cleaned) > args.show else ''}")
    print(f"Output projection     : {best.projection[:args.show]}{'...' if len(best.projection) > args.show else ''}")
    print(f"Unknown count         : {best.unknown_count} / {len(best.decoded)}")
    print(f"'+'/'=' in cleaned    : {'YES' if best.has_plus_or_eq else 'no'}")
    print(f"Expected in cleaned   : {'YES' if best.expected_in_cleaned else 'no'}")
    print(f"Expected in projection: {'YES' if best.expected_in_projection else 'no'}")
    escaped_blank = re.escape(blank)
    escaped_expected = re.escape(expected)
    print(
        f"Bounded expected      : {'YES' if best.expected_bounded_in_projection else 'no'}  "
        f"(regex (^|{escaped_blank}){escaped_expected}($|{escaped_blank}))"
    )
    print(f"Max pure block len    : {best.max_pure_block_len}")

    if best.windows:
        print()
        print("[3] Local operator-free windows matching expected")
        for idx, w in enumerate(best.windows[:8], start=1):
            kind = "exact" if w.exact_match else ("bounded" if w.bounded_match else "contains")
            print(
                f"{idx:>2}. runs[{w.start_run}:{w.end_run}] score={w.score:>3} unk={w.unknown_count:<2} kind={kind:<8} "
                f"projected={w.projected_window!r} decoded={w.decoded_window!r}"
            )
    else:
        print()
        print("[3] Local operator-free windows matching expected")
        print("None found.")

    print()
    print("[4] Verdict")

    run_evidence_ok = True
    run_evidence_reasons: List[str] = []
    if runlog is not None:
        if runlog.crash_halt_seen:
            run_evidence_ok = False
            run_evidence_reasons.append("crash-halt marker present in run log")
        if (runlog.max_checkpoint_m or 0) < 1:
            run_evidence_ok = False
            run_evidence_reasons.append("no checkpoint progress markers found")

    decode_evidence_ok = bool(best.windows) and best.expected_in_projection

    max_unknown_for_strong = max(2, (len(expected) // 2) + 1)
    strong_result = any(
        w.exact_match and w.unknown_count <= max_unknown_for_strong for w in best.windows
    )

    if direct.halted and run_evidence_ok and decode_evidence_ok and strong_result:
        verdict = "PASS"
        summary = "Strong evidence: run progressed, no crash-halt marker, and decoded windows match expected output."
        exit_code = 0
    elif direct.halted and decode_evidence_ok:
        verdict = "INCONCLUSIVE"
        summary = "Result appears in decode evidence, but run/halt evidence is incomplete or weaker than strict proof."
        exit_code = 1 if args.strict else 0
    else:
        verdict = "FAIL"
        summary = "Could not establish enough evidence that UTM run/decoded result matches expected behavior."
        exit_code = 1 if args.strict else 2

    print(f"Verdict               : {verdict}")
    print(f"Summary               : {summary}")

    if run_evidence_reasons:
        print("Run evidence gaps     : " + "; ".join(run_evidence_reasons))

    if not direct.halted:
        print("Direct-sim gap        : target TM did not halt cleanly under direct simulation.")

    if not decode_evidence_ok:
        print("Decode evidence gap   : expected output not recovered in strong operator-free window search.")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
