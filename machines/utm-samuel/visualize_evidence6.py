#!/usr/bin/env python3
import argparse
import html
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import decode_evidence6 as d6


def build_segments(tokens: Sequence[str]) -> List[Tuple[str, Tuple[int, int]]]:
    segments: List[Tuple[str, Tuple[int, int]]] = []

    largest = d6.largest_bd_segment(tokens)
    if largest[0] >= 0:
        segments.append(("largest_bd_segment", largest))

    land = d6.find_landmark(tokens)
    after = d6.segment_after_landmark(tokens, land)
    if after[0] >= 0:
        segments.append(("after_landmark", after))

    all_bd = sorted(d6.find_bd_segments(tokens), key=lambda ij: ij[1] - ij[0], reverse=True)
    for idx, seg in enumerate(all_bd[:4], start=1):
        segments.append((f"top_bd_segment_{idx}", seg))

    dedup: Dict[Tuple[int, int], str] = {}
    for label, seg in segments:
        if seg not in dedup:
            dedup[seg] = label

    out: List[Tuple[str, Tuple[int, int]]] = []
    for seg, label in dedup.items():
        out.append((label, seg))
    return out


def direct_trace(tm: dict, input_str: str, max_steps: int, radius: int = 10) -> List[Tuple[int, str, int, str, str]]:
    blank = tm.get("blank", ".")
    finals = set(tm["finals"])
    state = tm["initial"]
    tape = list(input_str)
    head = 0
    rows: List[Tuple[int, str, int, str, str]] = []

    def window_view() -> str:
        lo = max(0, head - radius)
        hi = min(len(tape), head + radius + 1)
        out = []
        for i in range(lo, hi):
            ch = tape[i]
            if i == head:
                out.append(f"[{ch}]")
            else:
                out.append(ch)
        return "".join(out)

    for step in range(max_steps + 1):
        if head < 0:
            tape = [blank] * (-head) + tape
            head = 0
        if head >= len(tape):
            tape.extend([blank] * (head - len(tape) + 1))

        if state in finals:
            rows.append((step, state, head, window_view(), "HALT (final state)"))
            break

        sym = tape[head]
        action = None
        for tr in tm["transitions"].get(state, []):
            if tr["read"] == sym:
                action = tr
                break

        if action is None:
            rows.append((step, state, head, window_view(), "CRASH (undefined transition)"))
            break

        action_txt = (
            f"read {action['read']} -> write {action['write']}, "
            f"move {action['action']}, next {action['to_state']}"
        )
        rows.append((step, state, head, window_view(), action_txt))

        tape[head] = action["write"]
        if action["action"] == "RIGHT":
            head += 1
        elif action["action"] == "LEFT":
            head -= 1
        state = action["to_state"]

    return rows


def render_raw_token_strip(tokens: Sequence[str], abs_start: int, abs_end: int, context: int) -> str:
    lo = max(0, abs_start - context)
    hi = min(len(tokens), abs_end + context)
    pieces: List[str] = []
    for i in range(lo, hi):
        tok = tokens[i]
        cls = "tok"
        if abs_start <= i < abs_end:
            cls += " sel"
        elif tok == "b":
            cls += " b"
        elif tok == "d":
            cls += " d"
        else:
            cls += " other"
        pieces.append(f"<span class='{cls}' title='idx={i}'>{html.escape(tok)}</span>")
    return " ".join(pieces)


def html_table(rows: List[List[str]], header: List[str]) -> str:
    out = ["<table><thead><tr>"]
    for h in header:
        out.append(f"<th>{html.escape(h)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for c in row:
            out.append(f"<td>{c}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def build_report(
    utm_out: str,
    tm_json: str,
    inp: str,
    run_log: str,
    out_html: str,
    max_steps: int,
    show_rows: int,
    context: int,
    radius: int,
) -> int:
    tm = d6.load_tm(tm_json)
    alphabet: List[str] = tm["alphabet"]
    blank: str = tm.get("blank", ".")
    target_state_count = len(tm["states"])
    q = len(alphabet)

    direct = d6.direct_simulate(tm, inp, max_steps)
    trace = direct_trace(tm, inp, max_steps=min(80, max_steps), radius=12)

    runlog = None
    if Path(run_log).exists():
        runlog = d6.parse_run_log(run_log)

    tokens, token_mode = d6.load_final_tape_tokens(utm_out)
    if not tokens:
        print("[FAIL] Empty utm output.")
        return 1

    decoded_segments: List[d6.SegmentDecode] = []
    all_candidates: List[d6.Candidate] = []
    for label, (seg_start, seg_end) in build_segments(tokens):
        if seg_end <= seg_start:
            continue
        seg_tokens = tokens[seg_start:seg_end]
        decoded = d6.decode_segment_strict(seg_tokens, alphabet, label, seg_start, seg_end)
        decoded_segments.append(decoded)
        all_candidates.extend(d6.build_ea_candidates(decoded, blank))

    matching_mode = "exact"
    matching = [c for c in all_candidates if c.trimmed == direct.expected_output]
    if not matching:
        matching_mode = "projected"
        matching = [
            c
            for c in all_candidates
            if d6.project_to_expected_symbols(c.trimmed, direct.expected_output) == direct.expected_output
        ]
    best_match, ambiguous = d6.choose_best_matching_candidate(matching, target_state_count)
    segment_index = {(s.label, s.seg_start, s.seg_end): s for s in decoded_segments}
    chosen_seg = None
    if best_match is not None:
        chosen_seg = segment_index.get((best_match.segment_label, best_match.seg_start, best_match.seg_end))

    run_ok = (
        runlog is not None
        and bool(runlog.checkpoints_unique)
        and (runlog.max_checkpoint_m or 0) >= 1
        and (not runlog.crash_halt_seen)
    )
    pass_v6 = run_ok and direct.halted and (not direct.crashed) and (best_match is not None) and (not ambiguous)

    explain_rows_html = "<p>No strict candidate was selected.</p>"
    neighborhood = ""
    raw_strip = ""
    if best_match is not None and chosen_seg is not None:
        strict = chosen_seg.strict_tokens
        lo = max(0, best_match.strict_start - radius)
        hi = min(len(strict), best_match.strict_end + radius)
        left = "".join((tok.symbol or "?") for tok in strict[lo:best_match.strict_start])
        mid = "".join((tok.symbol or "?") for tok in strict[best_match.strict_start:best_match.strict_end])
        right = "".join((tok.symbol or "?") for tok in strict[best_match.strict_end:hi])
        neighborhood = f"{html.escape(left)}<span class='mid'>[{html.escape(mid)}]</span>{html.escape(right)}"

        run_rows: List[List[str]] = []
        for sidx in range(lo, hi):
            tok = strict[sidx]
            in_window = best_match.strict_start <= sidx < best_match.strict_end
            is_head = tok.kind == "EA" and tok.run_idx == best_match.ea_run_idx
            mark = "."
            if in_window:
                mark = "*"
            if is_head and in_window:
                mark = "H*"
            elif is_head:
                mark = "H"

            formula = ""
            if tok.kind == "A" and tok.sym_idx is not None:
                formula = f"(b+1)/4={tok.sym_idx}"
            elif tok.kind == "EA" and tok.state_idx is not None and tok.sym_idx is not None:
                formula = f"b=4*q*j+(4*i-1) with q={q}, j={tok.state_idx}, i={tok.sym_idx}"

            meaning = "ordinary tape symbol"
            if tok.kind == "EA":
                meaning = f"head/state anchor (head on sym, state={tok.state_idx})"

            run_rows.append(
                [
                    html.escape(mark),
                    str(sidx),
                    str(tok.run_idx),
                    html.escape(tok.kind),
                    html.escape(str(tok.state_idx) if tok.state_idx is not None else "-"),
                    html.escape(tok.symbol or "-"),
                    str(tok.b_len),
                    str(tok.d_len_after),
                    html.escape(formula),
                    html.escape(meaning),
                ]
            )
        explain_rows_html = html_table(
            run_rows,
            ["mark", "sidx", "run", "kind", "state", "sym", "b_len", "d_len", "formula decode", "meaning"],
        )

        abs_start = best_match.seg_start + best_match.raw_rel_start
        abs_end = best_match.seg_start + best_match.raw_rel_end
        raw_strip = render_raw_token_strip(tokens, abs_start, abs_end, context)

    seg_rows = [
        [
            html.escape(seg.label),
            f"[{seg.seg_start},{seg.seg_end})",
            str(seg.run_count),
            str(seg.strict_count),
            str(seg.dropped_by_sep),
            str(seg.dropped_invalid),
        ]
        for seg in decoded_segments
    ]
    seg_table = html_table(seg_rows, ["segment", "bounds", "runs", "strict", "drop_sep", "drop_invalid"])

    trace_rows = [
        [
            str(step),
            html.escape(st),
            str(head),
            f"<code>{html.escape(view)}</code>",
            html.escape(action),
        ]
        for (step, st, head, view, action) in trace[:show_rows]
    ]
    trace_table = html_table(trace_rows, ["step", "state", "head", "local tape around head", "transition"])

    cp_timeline = ""
    if runlog is not None and runlog.checkpoints_unique:
        cp_timeline = ", ".join(f"{x}M" for x in runlog.checkpoints_unique[:12])
        if len(runlog.checkpoints_unique) > 12:
            cp_timeline += ", ..."

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>UTM Evidence Visualizer</title>
  <style>
    :root {{
      --bg: #f7f4ef;
      --ink: #1f2d3a;
      --muted: #5a6a78;
      --card: #ffffff;
      --line: #d3d6db;
      --ok: #0a7f41;
      --bad: #b42318;
      --accent: #0f6cbd;
      --sel: #fde68a;
      --b: #dbeafe;
      --d: #fee2e2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: radial-gradient(circle at 0% 0%, #fff8e8, var(--bg) 45%);
      color: var(--ink);
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      line-height: 1.35;
    }}
    main {{ max-width: 1180px; margin: 24px auto 56px; padding: 0 16px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-family: "IBM Plex Mono", monospace; font-size: 28px; letter-spacing: 0.2px; }}
    h2 {{ font-size: 20px; margin-top: 20px; }}
    .sub {{ color: var(--muted); margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .label {{ color: var(--muted); font-size: 13px; }}
    .value {{ font-family: "IBM Plex Mono", monospace; font-size: 14px; }}
    .ok {{ color: var(--ok); font-weight: 700; }}
    .bad {{ color: var(--bad); font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
    th, td {{
      border: 1px solid var(--line);
      padding: 6px 8px;
      font-size: 13px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f2f6fb; font-weight: 700; }}
    .legend {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 13px;
      margin: 8px 0;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 99px;
      padding: 4px 8px;
      background: #fff;
      font-family: "IBM Plex Mono", monospace;
    }}
    .tok {{ display: inline-block; padding: 0 4px; border-radius: 4px; font-family: "IBM Plex Mono", monospace; }}
    .tok.b {{ background: var(--b); }}
    .tok.d {{ background: var(--d); }}
    .tok.sel {{ background: var(--sel); font-weight: 700; }}
    .tok.other {{ background: #eee; }}
    code {{ font-family: "IBM Plex Mono", monospace; }}
    .mid {{ background: var(--sel); padding: 0 2px; border-radius: 4px; font-weight: 700; }}
    @media (max-width: 920px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>UTM Evidence Visualizer (v6 lens)</h1>
    <p class="sub">One page to explain: runtime encoding -> strict decode -> anchor-selected output.</p>

    <div class="grid">
      <section class="card">
        <h2>Run + Ground Truth</h2>
        <div class="label">TM file</div><div class="value">{html.escape(tm_json)}</div>
        <div class="label">Input</div><div class="value">{html.escape(repr(inp))}</div>
        <div class="label">UTM output source</div><div class="value">{html.escape(token_mode)} ({len(tokens)} tokens)</div>
        <div class="label">Expected output (direct TM)</div><div class="value">{html.escape(repr(direct.expected_output))}</div>
        <div class="label">Direct halt/crash</div><div class="value">{'halts' if direct.halted else 'not halted'} / {'crash' if direct.crashed else 'no crash'}</div>
        <div class="label">Run checkpoints</div><div class="value">{html.escape(cp_timeline or 'none')}</div>
        <div class="label">Crash marker in log</div><div class="value">{'YES' if (runlog and runlog.crash_halt_seen) else 'no'}</div>
        <div class="label">v6 verdict</div><div class="value {'ok' if pass_v6 else 'bad'}">{'PASS' if pass_v6 else 'FAIL'}</div>
      </section>

      <section class="card">
        <h2>How To Read This</h2>
        <p>Layer 1 is raw UTM tape symbols (<code>b/d</code> runs). Layer 2 decodes strict runs into symbols.</p>
        <p>Rows marked <code>EA</code> carry <b>head + state</b>: this is the anchor that pins where the machine currently is.</p>
        <p>Rows marked <code>A</code> are only decoded symbols without head/state location.</p>
        <p>Selected window is chosen around one anchor and must match expected output under v6 rules.</p>
        <div class="legend">
          <span class="pill">* = selected window token</span>
          <span class="pill">H* = head/state anchor inside window</span>
          <span class="pill">b = blue (run payload)</span>
          <span class="pill">d = red (separators)</span>
          <span class="pill">yellow = raw token span used by chosen window</span>
        </div>
      </section>
    </div>

    <section class="card">
      <h2>Candidate Segments</h2>
      {seg_table}
      <p class="sub">Only strict-decodable runs are kept: exact formulas + separator rule (<code>d_len_after == 1</code>).</p>
    </section>

    <section class="card">
      <h2>Decoded Neighborhood Around Chosen Window</h2>
      <p><code>{neighborhood or 'n/a'}</code></p>
      <p class="sub">Brackets show selected output window. The anchor row (EA) tells where head/state lives.</p>
      {explain_rows_html}
    </section>

    <section class="card">
      <h2>Raw UTM Tape Around Chosen Span</h2>
      <p>{raw_strip or 'n/a'}</p>
      <p class="sub">This is the actual token stream from <code>utm_out</code>. Yellow portion is the exact token span mapped to the chosen strict window.</p>
    </section>

    <section class="card">
      <h2>Direct TM Step Trace (for mental model)</h2>
      {trace_table}
      <p class="sub">This is not U9,3 internals; it is the original TM simulation on your input, shown to connect expected output with state/head movement.</p>
    </section>
  </main>
</body>
</html>"""

    Path(out_html).write_text(html_doc, encoding="utf-8")
    print(f"[OK] wrote {out_html}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate HTML visual explanation for strict decode evidence (v6)")
    ap.add_argument("utm_out")
    ap.add_argument("tm_json")
    ap.add_argument("--input", dest="inp", required=True)
    ap.add_argument("--run-log", required=True)
    ap.add_argument("--out", default="machines/utm-samuel/evidence6_report.html")
    ap.add_argument("--max-steps", type=int, default=200000)
    ap.add_argument("--rows", type=int, default=40, help="max direct-trace rows to show")
    ap.add_argument("--context", type=int, default=120, help="raw token context around chosen span")
    ap.add_argument("--radius", type=int, default=8, help="strict decoded tokens shown around chosen window")
    args = ap.parse_args()

    return build_report(
        utm_out=args.utm_out,
        tm_json=args.tm_json,
        inp=args.inp,
        run_log=args.run_log,
        out_html=args.out,
        max_steps=args.max_steps,
        show_rows=args.rows,
        context=args.context,
        radius=args.radius,
    )


if __name__ == "__main__":
    raise SystemExit(main())

