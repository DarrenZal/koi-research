#!/usr/bin/env python3
"""
Compare hallucination detection output against a committed baseline.

This script reads the output from verify-citations.py (citation_verification.json)
and compares it against a baseline to detect regressions in hallucination rate.

Traffic Light Status:
  - green: rate <= threshold AND rate <= baseline + delta_yellow
  - yellow: rate > baseline + delta_yellow but <= threshold AND < baseline + delta_red
  - red: rate > threshold OR rate >= baseline + delta_red
  - no_baseline: baseline file missing or has too few citations
  - insufficient_data: current run has too few citations for valid comparison

Example Usage:
--------------

# Basic comparison against baseline
python compare_hallucination_baseline.py \\
    --current citation_verification.json \\
    --baseline reports/baselines/prod/hallucination.json

# Full CI run with outputs and custom threshold
python compare_hallucination_baseline.py \\
    --current citation_verification.json \\
    --baseline reports/baselines/prod/hallucination.json \\
    --threshold 0.15 \\
    --min-citations 20 \\
    --out-json reports/evals/hallucination_diff.json \\
    --out-md reports/evals/hallucination_diff.md \\
    --fail-on red

# Refresh baseline with current results (after verified improvement)
python compare_hallucination_baseline.py \\
    --current citation_verification.json \\
    --baseline reports/baselines/prod/hallucination.json \\
    --write-baseline

# Strict mode: fail on any regression (yellow or red)
python compare_hallucination_baseline.py \\
    --current citation_verification.json \\
    --baseline reports/baselines/prod/hallucination.json \\
    --fail-on yellow

JSON Output Shape:
------------------
{
  "suite": "hallucination",
  "generated_at": "2026-01-08T12:00:00+00:00",
  "status": "green|yellow|red|no_baseline|insufficient_data",
  "current": {
    "hallucination_rate": 0.12,
    "total_citations": 50,
    "verified_count": 44,
    "failed_count": 6,
    "skipped_count": 0
  },
  "baseline": { ... },
  "delta": 0.02,
  "threshold": 0.20,
  "reason": "within thresholds"
}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _extract_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_at": payload.get("generated_at") or payload.get("generatedAt") or "",
        "source_file": payload.get("source_file") or "",
        "total_citations": int(payload.get("total_citations") or 0),
        "verified_count": int(payload.get("verified_count") or 0),
        "failed_count": int(payload.get("failed_count") or 0),
        "skipped_count": int(payload.get("skipped_count") or 0),
        "hallucination_rate": float(payload.get("hallucination_rate") or 0.0),
    }


def _traffic_light(
    *,
    current_total: int,
    current_rate: float,
    threshold: float,
    baseline_total: Optional[int],
    baseline_rate: Optional[float],
    min_citations: int,
    delta_yellow: float,
    delta_red: float,
) -> Dict[str, Any]:
    if current_total < min_citations:
        return {
            "status": "insufficient_data",
            "reason": f"total_citations<{min_citations} (current_total={current_total})",
        }

    if current_rate > threshold:
        return {
            "status": "red",
            "reason": f"hallucination_rate>{threshold:.2f} (current_rate={current_rate:.3f})",
        }

    if baseline_total is None or baseline_rate is None or baseline_total < min_citations:
        return {
            "status": "no_baseline",
            "reason": f"baseline missing or baseline_total<{min_citations}",
        }

    delta = current_rate - baseline_rate
    if delta >= delta_red:
        return {"status": "red", "reason": f"rate regression >= {delta_red:.2f} (delta={delta:.3f})"}
    if delta >= delta_yellow:
        return {"status": "yellow", "reason": f"rate regression >= {delta_yellow:.2f} (delta={delta:.3f})"}

    return {"status": "green", "reason": "within thresholds"}


def _render_md(report: Dict[str, Any]) -> str:
    status = report.get("status") or ""
    cur = report.get("current") or {}
    base = report.get("baseline") or {}
    delta = report.get("delta")

    lines = []
    lines.append("# Hallucination Baseline Diff")
    lines.append("")
    lines.append(f"- **Status:** {status}")
    if report.get("reason"):
        lines.append(f"- **Reason:** {report['reason']}")
    lines.append("")
    lines.append("| Metric | Baseline | Current | Δ |")
    lines.append("|--------|----------|---------|---|")
    lines.append(
        f"| Hallucination rate | {base.get('hallucination_rate','')} | {cur.get('hallucination_rate','')} | {delta if delta is not None else ''} |"
    )
    lines.append(
        f"| Total citations | {base.get('total_citations','')} | {cur.get('total_citations','')} | |"
    )
    lines.append(
        f"| Verified | {base.get('verified_count','')} | {cur.get('verified_count','')} | |"
    )
    lines.append(
        f"| Failed | {base.get('failed_count','')} | {cur.get('failed_count','')} | |"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare citation verification JSON to a committed baseline.")
    parser.add_argument("--current", required=True, help="Path to current citation_verification.json")
    parser.add_argument("--baseline", required=True, help="Path to baseline JSON")
    parser.add_argument("--min-citations", type=int, default=10, help="Min citations required for baseline diff (default: 10)")
    parser.add_argument("--threshold", type=float, default=0.20, help="Absolute hallucination rate threshold (default: 0.20)")
    parser.add_argument("--delta-yellow", type=float, default=0.05, help="Yellow regression delta vs baseline (default: 0.05)")
    parser.add_argument("--delta-red", type=float, default=0.10, help="Red regression delta vs baseline (default: 0.10)")
    parser.add_argument("--out-json", default="", help="Write diff JSON report to this path")
    parser.add_argument("--out-md", default="", help="Write diff Markdown report to this path")
    parser.add_argument("--write-baseline", action="store_true", help="Overwrite baseline with current summary and exit 0")
    parser.add_argument("--fail-on", choices=["red", "yellow"], default="red", help="Exit non-zero on this status")
    args = parser.parse_args()

    current_path = Path(args.current)
    baseline_path = Path(args.baseline)
    current_raw = _read_json(current_path)
    current = _extract_summary(current_raw)
    current["generated_at"] = _now_iso()

    if args.write_baseline:
        baseline_payload = {
            "suite": "hallucination",
            "generated_at": current["generated_at"],
            "min_citations": args.min_citations,
            "threshold": args.threshold,
            "summary": current,
        }
        _write_json(baseline_path, baseline_payload)
        print(f"Wrote baseline: {baseline_path}")
        return 0

    baseline_raw: Optional[Dict[str, Any]] = None
    baseline_summary: Optional[Dict[str, Any]] = None
    if baseline_path.exists():
        baseline_raw = _read_json(baseline_path)
        maybe = baseline_raw.get("summary")
        if isinstance(maybe, dict):
            baseline_summary = _extract_summary(maybe)
        else:
            baseline_summary = _extract_summary(baseline_raw)

    baseline_total = baseline_summary.get("total_citations") if baseline_summary else None
    baseline_rate = baseline_summary.get("hallucination_rate") if baseline_summary else None

    traffic = _traffic_light(
        current_total=current["total_citations"],
        current_rate=current["hallucination_rate"],
        threshold=args.threshold,
        baseline_total=baseline_total,
        baseline_rate=baseline_rate,
        min_citations=args.min_citations,
        delta_yellow=args.delta_yellow,
        delta_red=args.delta_red,
    )

    delta = None
    if baseline_rate is not None and isinstance(baseline_rate, (float, int)):
        delta = float(current["hallucination_rate"]) - float(baseline_rate)

    report = {
        "suite": "hallucination",
        "generated_at": _now_iso(),
        "current_path": str(current_path),
        "baseline_path": str(baseline_path),
        "min_citations": args.min_citations,
        "threshold": args.threshold,
        "delta_yellow": args.delta_yellow,
        "delta_red": args.delta_red,
        "status": traffic["status"],
        "reason": traffic.get("reason") or "",
        "baseline": baseline_summary or {},
        "current": current,
        "delta": delta,
    }

    if args.out_json:
        _write_json(Path(args.out_json), report)
    if args.out_md:
        _write_text(Path(args.out_md), _render_md(report))

    status = report["status"]
    if args.fail_on == "yellow" and status in ("yellow", "red"):
        print(f"Hallucination diff status: {status}", file=sys.stderr)
        return 1
    if args.fail_on == "red" and status == "red":
        print(f"Hallucination diff status: {status}", file=sys.stderr)
        return 1

    print(f"Hallucination diff status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

