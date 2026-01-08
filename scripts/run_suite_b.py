#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> Tuple[Dict[str, Any], int]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url=url, data=data, method="POST")
    for k, v in headers.items():
        request.add_header(k, v)
    request.add_header("Content-Type", "application/json")

    start = time.time()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            duration_ms = int((time.time() - start) * 1000)
            return json.loads(body), duration_ms
    except urllib.error.HTTPError as e:
        duration_ms = int((time.time() - start) * 1000)
        raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        raise RuntimeError(f"HTTP {e.code} from {url}: {raw[:500]}") from e
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        raise RuntimeError(f"Request failed after {duration_ms}ms: {url}: {e}") from e


def _extract_as_of(payload: Dict[str, Any]) -> Dict[str, str]:
    koi = (payload.get("as_of") or {}).get("koi") or {}
    return {
        "corpus_version": koi.get("corpus_version") or "",
        "indexed_at": koi.get("indexed_at") or "",
    }


def _extract_candidates(tool: str, payload: Dict[str, Any], k: int) -> List[Dict[str, Any]]:
    data = payload.get("data") or {}
    results = data.get("results") or []
    candidates: List[Dict[str, Any]] = []

    if tool == "query":
        for r in results[:k]:
            meta = r.get("metadata") or {}
            candidates.append(
                {
                    "rid": r.get("rid") or "",
                    "title": r.get("title") or "",
                    "url": meta.get("url") or "",
                    "base_rid": meta.get("base_rid") or "",
                    "score": r.get("score"),
                }
            )
        return candidates

    if tool == "graph":
        for r in results[:k]:
            ent = r.get("entity") or {}
            candidates.append(
                {
                    "entity_name": ent.get("name") or "",
                    "repo": ent.get("repo") or "",
                    "file_path": ent.get("file_path") or "",
                    "github_url": ent.get("github_url") or "",
                    "entity_type": ent.get("type") or "",
                    "raw_type": r.get("type") or "",
                }
            )
        return candidates

    raise ValueError(f"Unknown tool: {tool}")


def _match_condition(
    condition: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    cond_type = condition.get("type")
    values = condition.get("values") or []
    if not isinstance(cond_type, str) or not isinstance(values, list) or not values:
        return {"hit": False, "first_rank": None, "matched_value": None, "type": cond_type}

    for idx, c in enumerate(candidates, start=1):
        for v in values:
            if not isinstance(v, str):
                continue

            if cond_type == "url_contains":
                if v in (c.get("url") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "rid_contains":
                if v in (c.get("rid") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "base_rid_contains":
                if v in (c.get("base_rid") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "title_contains":
                if v in (c.get("title") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "entity_name_equals":
                if v == (c.get("entity_name") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "entity_name_contains":
                if v in (c.get("entity_name") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            elif cond_type == "file_path_contains":
                if v in (c.get("file_path") or ""):
                    return {"hit": True, "first_rank": idx, "matched_value": v, "type": cond_type}
            else:
                return {"hit": False, "first_rank": None, "matched_value": None, "type": cond_type}

    return {"hit": False, "first_rank": None, "matched_value": None, "type": cond_type}


def _evaluate_test(test: Dict[str, Any], koi_api_endpoint: str, k: int) -> Dict[str, Any]:
    test_id = test.get("id") or "<missing-id>"
    tool = test.get("tool")
    if tool not in ("query", "graph"):
        raise ValueError(f"{test_id}: tool must be 'query' or 'graph'")

    endpoint = koi_api_endpoint.rstrip("/")
    url = f"{endpoint}/query" if tool == "query" else f"{endpoint}/graph"

    headers = {
        "X-User-Email": os.environ.get("KOI_USER_EMAIL", "suite-b-eval@local"),
    }

    payload, duration_ms = _http_post_json(url=url, payload=test.get("input") or {}, headers=headers)
    as_of = _extract_as_of(payload)
    candidates = _extract_candidates(tool=tool, payload=payload, k=k)

    assertion = test.get("assert") or {}
    min_results = int(assertion.get("min_results") or 0)
    required_matches = assertion.get("required_matches") or []

    min_results_ok = len(candidates) >= min_results if min_results else True
    match_results = []
    ranks: List[int] = []
    for cond in required_matches:
        result = _match_condition(cond, candidates)
        match_results.append(result)
        if result.get("hit") and isinstance(result.get("first_rank"), int):
            ranks.append(int(result["first_rank"]))

    required_ok = all(bool(r.get("hit")) for r in match_results) if required_matches else True
    hit = bool(min_results_ok and required_ok)

    hit_rank_best = min(ranks) if ranks else None
    hit_rank_worst = max(ranks) if ranks else None

    observed_top = []
    if tool == "query":
        observed_top = [c.get("url") or c.get("rid") or "" for c in candidates][:k]
    elif tool == "graph":
        observed_top = [c.get("entity_name") or "" for c in candidates][:k]

    return {
        "id": test_id,
        "tool": tool,
        "critical": bool(test.get("critical")),
        "notes": test.get("notes") or "",
        "input": test.get("input") or {},
        "assert": assertion,
        "hit": hit,
        "min_results_ok": min_results_ok,
        "required_matches": match_results,
        "hit_rank_best": hit_rank_best,
        "hit_rank_worst": hit_rank_worst,
        "observed_top": observed_top,
        "latency_ms": duration_ms,
        "as_of": as_of,
    }


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.get("hit") is True)
    failed = total - passed
    pass_rate = (passed / total) if total else 0.0
    ranks = [r.get("hit_rank_worst") for r in results if isinstance(r.get("hit_rank_worst"), int)]
    avg_hit_rank = (sum(ranks) / len(ranks)) if ranks else None
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "avg_hit_rank_worst": avg_hit_rank,
    }


def _diff_vs_baseline(
    baseline: Dict[str, Any],
    current_results: List[Dict[str, Any]],
    pass_rate_drop_red: float,
    pass_rate_drop_yellow: float,
    rank_regression_threshold: int,
) -> Dict[str, Any]:
    baseline_results = baseline.get("tests") or []
    baseline_by_id = {r.get("id"): r for r in baseline_results if isinstance(r, dict) and r.get("id")}
    current_by_id = {r.get("id"): r for r in current_results if isinstance(r, dict) and r.get("id")}

    regressions: List[Dict[str, Any]] = []
    improvements: List[Dict[str, Any]] = []
    rank_regressions: List[Dict[str, Any]] = []

    critical_regressions: List[str] = []

    for test_id, cur in current_by_id.items():
        base = baseline_by_id.get(test_id)
        if not base:
            continue

        base_hit = bool(base.get("hit") is True)
        cur_hit = bool(cur.get("hit") is True)

        if base_hit and not cur_hit:
            regressions.append({"id": test_id})
            if cur.get("critical") is True or base.get("critical") is True:
                critical_regressions.append(test_id)
            continue

        if (not base_hit) and cur_hit:
            improvements.append({"id": test_id})
            continue

        if base_hit and cur_hit:
            base_rank = base.get("hit_rank_worst") or base.get("hit_rank_best")
            cur_rank = cur.get("hit_rank_worst") or cur.get("hit_rank_best")
            if isinstance(base_rank, int) and isinstance(cur_rank, int):
                delta = cur_rank - base_rank
                if delta >= rank_regression_threshold:
                    rank_regressions.append(
                        {"id": test_id, "baseline_rank": int(base_rank), "current_rank": int(cur_rank), "delta": int(delta)}
                    )

    base_pass_rate = float((baseline.get("summary") or {}).get("pass_rate") or 0.0)
    cur_pass_rate = float(_summarize(current_results).get("pass_rate") or 0.0)
    pass_rate_drop = base_pass_rate - cur_pass_rate

    status = "green"
    if critical_regressions or pass_rate_drop >= pass_rate_drop_red:
        status = "red"
    elif regressions or pass_rate_drop >= pass_rate_drop_yellow:
        status = "yellow"

    return {
        "status": status,
        "baseline_generated_at": baseline.get("generated_at") or "",
        "baseline_as_of": baseline.get("as_of") or {},
        "baseline_pass_rate": base_pass_rate,
        "current_pass_rate": cur_pass_rate,
        "pass_rate_drop": pass_rate_drop,
        "regressions": regressions,
        "critical_regressions": critical_regressions,
        "improvements": improvements,
        "rank_regressions": rank_regressions,
    }


def _render_markdown_report(
    suite: str,
    env_name: str,
    koi_api_endpoint: str,
    k: int,
    generated_at: str,
    as_of: Dict[str, str],
    summary: Dict[str, Any],
    baseline_diff: Optional[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append(f"# {suite.upper()} Retrieval Eval Report ({env_name})")
    lines.append("")
    lines.append(f"- **Generated at:** {generated_at}")
    lines.append(f"- **KOI API:** {koi_api_endpoint}")
    lines.append(f"- **k:** {k}")
    if as_of.get("corpus_version") or as_of.get("indexed_at"):
        lines.append(f"- **Corpus version:** {as_of.get('corpus_version') or 'unknown'}")
        lines.append(f"- **Indexed at:** {as_of.get('indexed_at') or 'unknown'}")
    lines.append("")

    if baseline_diff:
        lines.append("## Baseline Diff")
        lines.append("")
        lines.append(f"- **Status:** {baseline_diff.get('status')}")
        lines.append(f"- **Baseline pass_rate:** {baseline_diff.get('baseline_pass_rate'):.2f}")
        lines.append(f"- **Current pass_rate:** {baseline_diff.get('current_pass_rate'):.2f}")
        lines.append(f"- **Pass rate drop:** {baseline_diff.get('pass_rate_drop'):.2f}")
        if baseline_diff.get("critical_regressions"):
            lines.append(f"- **Critical regressions:** {', '.join(baseline_diff['critical_regressions'])}")
        if baseline_diff.get("regressions"):
            lines.append(f"- **Regressions:** {', '.join(r['id'] for r in baseline_diff['regressions'])}")
        if baseline_diff.get("rank_regressions"):
            lines.append(
                f"- **Rank regressions:** {', '.join(r['id'] for r in baseline_diff['rank_regressions'])}"
            )
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total:** {summary.get('total')}")
    lines.append(f"- **Passed:** {summary.get('passed')}")
    lines.append(f"- **Failed:** {summary.get('failed')}")
    lines.append(f"- **Pass rate:** {summary.get('pass_rate'):.2f}")
    if summary.get("avg_hit_rank_worst") is not None:
        lines.append(f"- **Avg hit rank (worst):** {summary.get('avg_hit_rank_worst'):.2f}")
    lines.append("")

    lines.append("## Results")
    lines.append("")
    lines.append("| Test | Tool | Hit | Rank (worst) | Critical | Latency (ms) |")
    lines.append("|------|------|-----|--------------|----------|--------------|")
    for r in results:
        hit = "✅" if r.get("hit") else "❌"
        rank = r.get("hit_rank_worst") if r.get("hit_rank_worst") is not None else ""
        critical = "Y" if r.get("critical") else ""
        lines.append(f"| {r.get('id')} | {r.get('tool')} | {hit} | {rank} | {critical} | {r.get('latency_ms','')} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("Each test is a deterministic top-k expectation against KOI `/query` or `/graph`.")
    lines.append("If a test regresses, inspect the `observed_top` list in the JSON report for what replaced the expected hit.")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Suite B retrieval evals against KOI HTTP endpoints.")
    parser.add_argument("--env", default="prod", help="Environment label used in report paths (default: prod)")
    parser.add_argument(
        "--koi-api-endpoint",
        default=os.environ.get("KOI_API_ENDPOINT", "https://regen.gaiaai.xyz/api/koi"),
        help="KOI API base URL (default: env KOI_API_ENDPOINT or prod)",
    )
    parser.add_argument("--gold", default="evals/suite_b_gold_set.json", help="Path to gold set JSON")
    parser.add_argument("--k", type=int, default=10, help="Top-k to evaluate (default: 10)")
    parser.add_argument("--baseline", default="reports/baselines/prod/suite_b.json", help="Path to baseline JSON")
    parser.add_argument("--out-json", default="", help="Write run JSON report to this path")
    parser.add_argument("--out-md", default="", help="Write run Markdown report to this path")
    parser.add_argument("--write-baseline", default="", help="Write current run as a new baseline JSON to this path")
    parser.add_argument("--fail-on", choices=["red", "yellow"], default="red", help="Exit non-zero on this status")
    args = parser.parse_args()

    gold_path = Path(args.gold)
    gold = _read_json(gold_path)
    suite = gold.get("suite") or "suite_b"
    tests = gold.get("tests") or []
    if not isinstance(tests, list) or not tests:
        print(f"No tests found in {gold_path}", file=sys.stderr)
        return 2

    generated_at = _now_iso()
    koi_api_endpoint = str(args.koi_api_endpoint)
    k = int(args.k)

    results: List[Dict[str, Any]] = []
    as_of: Dict[str, str] = {"corpus_version": "", "indexed_at": ""}

    for t in tests:
        if not isinstance(t, dict):
            continue
        r = _evaluate_test(t, koi_api_endpoint=koi_api_endpoint, k=k)
        results.append(r)
        if not as_of.get("corpus_version") and r.get("as_of"):
            as_of = r["as_of"]

    summary = _summarize(results)

    baseline_diff: Optional[Dict[str, Any]] = None
    baseline_path = Path(args.baseline) if args.baseline else None
    if baseline_path and baseline_path.exists():
        baseline_payload = _read_json(baseline_path)
        baseline_diff = _diff_vs_baseline(
            baseline=baseline_payload,
            current_results=results,
            pass_rate_drop_red=0.10,
            pass_rate_drop_yellow=0.05,
            rank_regression_threshold=3,
        )

    output = {
        "suite": suite,
        "env": args.env,
        "generated_at": generated_at,
        "koi_api_endpoint": koi_api_endpoint,
        "k": k,
        "as_of": as_of,
        "summary": summary,
        "baseline_diff": baseline_diff,
        "tests": results,
    }

    if args.out_json:
        _write_json(Path(args.out_json), output)

    md = _render_markdown_report(
        suite=suite,
        env_name=args.env,
        koi_api_endpoint=koi_api_endpoint,
        k=k,
        generated_at=generated_at,
        as_of=as_of,
        summary=summary,
        baseline_diff=baseline_diff,
        results=results,
    )
    if args.out_md:
        _write_text(Path(args.out_md), md)

    if args.write_baseline:
        baseline_out = dict(output)
        baseline_out["baseline_diff"] = None
        _write_json(Path(args.write_baseline), baseline_out)

    status = (baseline_diff or {}).get("status") if baseline_diff else "no_baseline"
    if status == "no_baseline":
        print("Suite B: no baseline found; generated report only.")
        return 0

    if args.fail_on == "yellow" and status in ("yellow", "red"):
        print(f"Suite B status: {status} (fail_on={args.fail_on})", file=sys.stderr)
        return 1
    if args.fail_on == "red" and status == "red":
        print(f"Suite B status: {status} (fail_on={args.fail_on})", file=sys.stderr)
        return 1

    print(f"Suite B status: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

