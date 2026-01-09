#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import string
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _rand_suffix(n: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _substitute(template: str, variables: Dict[str, str]) -> str:
    out = template
    for k, v in variables.items():
        out = out.replace(f"{{{{{k}}}}}", v)
    return out


def _as_repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except Exception:
        return str(path)


def _glob_any(repo_root: Path, pattern: str) -> List[Path]:
    # Use pathlib glob from repo root to keep paths deterministic.
    return list(repo_root.glob(pattern))


def _check_path_exists(repo_root: Path, path_template: str, variables: Dict[str, str]) -> Tuple[bool, str]:
    path = _substitute(path_template, variables)
    p = (repo_root / path).resolve()
    return p.exists(), path


def _check_glob_exists(repo_root: Path, pattern_template: str, variables: Dict[str, str]) -> Tuple[bool, str, int]:
    pattern = _substitute(pattern_template, variables)
    matches = _glob_any(repo_root, pattern)
    return len(matches) > 0, pattern, len(matches)


def _check_file_contains(
    repo_root: Path, path_template: str, contains: List[str], variables: Dict[str, str]
) -> Tuple[bool, str, List[str]]:
    rel = _substitute(path_template, variables)
    p = (repo_root / rel).resolve()
    if not p.exists() or not p.is_file():
        return False, rel, [f"missing file: {rel}"]
    text = p.read_text(encoding="utf-8", errors="replace")
    missing = [s for s in contains if s not in text]
    return len(missing) == 0, rel, missing


def _normalize_tool_name(name: str) -> str:
    return name.strip().lower()


def _tool_matches_contains(tool_name: str, needle: str) -> bool:
    return needle.lower() in _normalize_tool_name(tool_name)


def _is_bash_tool(tool_name: str) -> bool:
    t = _normalize_tool_name(tool_name)
    return t == "bash" or t.endswith(".bash") or "bash" in t


def _extract_bash_command(tool_input: Dict[str, Any]) -> str:
    # Common schemas: {"command": "..."} or {"cmd": "..."}.
    if isinstance(tool_input.get("command"), str):
        return tool_input["command"]
    if isinstance(tool_input.get("cmd"), str):
        return tool_input["cmd"]
    return ""


def _render_md_report(run: Dict[str, Any]) -> str:
    if run.get("suite") == "suite_d_delta":
        return _render_md_report_delta(run)

    lines: List[str] = []
    lines.append(f"# Suite D Agent Scenario Results ({run.get('env')})")
    lines.append("")
    lines.append(f"- **Generated at:** {run.get('generated_at')}")
    lines.append(f"- **Model:** {run.get('model')}")
    lines.append(f"- **KOI API:** {run.get('koi_api_endpoint')}")
    lines.append("")

    summary = run.get("summary") or {}
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total:** {summary.get('total')}")
    lines.append(f"- **Passed:** {summary.get('passed')}")
    lines.append(f"- **Failed:** {summary.get('failed')}")
    lines.append("")

    lines.append("## Scenarios")
    lines.append("")
    for s in run.get("scenarios", []):
        status = "✅ PASS" if s.get("passed") else "❌ FAIL"
        lines.append(f"### {s.get('id')} — {s.get('name')} ({status})")
        lines.append("")
        lines.append(f"- **Run ID:** {s.get('run_id')}")
        lines.append(f"- **Duration:** {s.get('duration_ms')} ms")
        if s.get("failures"):
            lines.append(f"- **Failures:** {', '.join(s['failures'])}")
        if s.get("tool_error_count", 0) > 0:
            lines.append(f"- **Tool errors:** {s.get('tool_error_count')}")
        lines.append("")
        lines.append("**Tool calls (names):**")
        tool_names = s.get("tool_calls") or []
        if tool_names:
            lines.append("```text")
            for t in tool_names[:50]:
                lines.append(str(t))
            if len(tool_names) > 50:
                lines.append(f"... ({len(tool_names) - 50} more)")
            lines.append("```")
        else:
            lines.append("_No tool calls captured._")
        lines.append("")

        # Include a short excerpt of assistant output to help debugging.
        out = (s.get("assistant_text") or "").strip()
        if out:
            excerpt = out[:2000]
            lines.append("**Assistant output (truncated):**")
            lines.append("```text")
            lines.append(excerpt)
            if len(out) > len(excerpt):
                lines.append("... (truncated)")
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def _render_md_report_delta(run: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Suite D Delta (KOI Value-Add) Results ({run.get('env')})")
    lines.append("")
    lines.append(f"- **Generated at:** {run.get('generated_at')}")
    lines.append(f"- **Model:** {run.get('model')}")
    lines.append(f"- **KOI API:** {run.get('koi_api_endpoint')}")
    lines.append("")

    summary = (run.get("koi_value_add_delta") or {}).get("summary") or {}
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Overall status:** {summary.get('status')}")
    lines.append(f"- **Pairs:** {summary.get('total_pairs')} (green={summary.get('green')}, yellow={summary.get('yellow')}, red={summary.get('red')})")
    if summary.get("avg_verified_rate_delta") is not None:
        lines.append(f"- **Avg verified_rate Δ (koi-baseline):** {summary.get('avg_verified_rate_delta'):.3f}")
    if summary.get("avg_citations_delta") is not None:
        lines.append(f"- **Avg citations Δ (koi-baseline):** {summary.get('avg_citations_delta'):.2f}")
    lines.append("")

    lines.append("## Pairs")
    lines.append("")
    for p in run.get("pairs", []):
        status = p.get("status") or "unknown"
        lines.append(f"### {p.get('id')} — {p.get('name')} ({status})")
        if p.get("reason"):
            lines.append(f"- **Reason:** {p.get('reason')}")

        base = p.get("baseline") or {}
        koi = p.get("koi") or {}
        delta = p.get("delta") or {}

        lines.append("")
        lines.append("| Metric | Baseline | KOI | Δ |")
        lines.append("|--------|----------|-----|---|")
        lines.append(
            f"| Duration (ms) | {base.get('duration_ms','')} | {koi.get('duration_ms','')} | {delta.get('duration_ms_delta','')} |"
        )
        lines.append(
            f"| Tool calls | {base.get('tool_calls_total','')} | {koi.get('tool_calls_total','')} | {delta.get('tool_calls_total_delta','')} |"
        )
        lines.append(
            f"| Citations (total) | {base.get('citations',{}).get('total_citations','')} | {koi.get('citations',{}).get('total_citations','')} | {delta.get('citations_total_delta','')} |"
        )
        lines.append(
            f"| Verifiable citations | {base.get('citations',{}).get('verifiable_citations','')} | {koi.get('citations',{}).get('verifiable_citations','')} | {delta.get('verifiable_citations_delta','')} |"
        )
        lines.append(
            f"| Verified rate | {base.get('citations',{}).get('verified_rate','')} | {koi.get('citations',{}).get('verified_rate','')} | {delta.get('verified_rate_delta','')} |"
        )
        lines.append(
            f"| Hallucination rate | {base.get('citations',{}).get('hallucination_rate','')} | {koi.get('citations',{}).get('hallucination_rate','')} | {delta.get('hallucination_rate_delta','')} |"
        )
        lines.append("")

    return "\n".join(lines)


async def _run_prompt_with_sdk(
    prompt: str,
    *,
    cwd: Path,
    model: str,
    koi_api_endpoint: str,
    enable_mcp: bool,
    stderr_lines: List[str],
) -> Dict[str, Any]:
    try:
        from claude_agent_sdk import ClaudeAgentOptions, query
        from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, TextBlock
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "Claude Agent SDK is not installed. Install with: python3 -m pip install claude-agent-sdk"
        ) from e

    def _stderr_cb(line: str) -> None:
        stderr_lines.append(line.rstrip("\n"))

    mcp_servers: Dict[str, Any] = {}
    if enable_mcp:
        # Stdio MCP server running regen-koi-mcp via npx.
        mcp_env: Dict[str, str] = {"KOI_API_ENDPOINT": koi_api_endpoint}
        if os.environ.get("KOI_AUTH_TOKEN"):
            mcp_env["KOI_AUTH_TOKEN"] = os.environ["KOI_AUTH_TOKEN"]
        if os.environ.get("KOI_USER_EMAIL"):
            mcp_env["KOI_USER_EMAIL"] = os.environ["KOI_USER_EMAIL"]

        mcp_servers = {
            "regen-koi": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "regen-koi-mcp@latest"],
                "env": mcp_env,
            }
        }

    options = ClaudeAgentOptions(
        tools={"type": "preset", "preset": "claude_code"},
        permission_mode="bypassPermissions",
        model=model,
        cwd=str(cwd),
        mcp_servers=mcp_servers,
        stderr=_stderr_cb,
    )

    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []
    assistant_text_parts: List[str] = []
    result: Dict[str, Any] = {}

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    assistant_text_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls.append({"id": block.id, "name": block.name, "input": block.input})
                elif isinstance(block, ToolResultBlock):
                    tool_results.append(
                        {
                            "tool_use_id": block.tool_use_id,
                            "is_error": block.is_error,
                            "content": block.content,
                        }
                    )
        elif isinstance(message, ResultMessage):
            result = asdict(message)

    return {
        "assistant_text": "".join(assistant_text_parts),
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "result": result,
    }


def _evaluate_checks(
    scenario: Dict[str, Any],
    *,
    repo_root: Path,
    variables: Dict[str, str],
    tool_calls: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    checks = scenario.get("checks") or {}
    failures: List[str] = []

    for p in checks.get("path_exists", []) or []:
        ok, resolved = _check_path_exists(repo_root, p, variables)
        if not ok:
            failures.append(f"missing path: {resolved}")

    for g in checks.get("glob_exists", []) or []:
        ok, pattern, count = _check_glob_exists(repo_root, g, variables)
        if not ok:
            failures.append(f"glob has no matches: {pattern}")
        else:
            # Optional sanity: avoid pattern silently matching thousands of files.
            if count > 500:
                failures.append(f"glob matched too many files ({count}): {pattern}")

    for fc in checks.get("file_contains", []) or []:
        path_t = fc.get("path")
        contains = fc.get("contains") or []
        if not isinstance(path_t, str) or not isinstance(contains, list):
            continue
        ok, rel, missing = _check_file_contains(repo_root, path_t, [str(x) for x in contains], variables)
        if not ok:
            if missing and missing[0].startswith("missing file:"):
                failures.append(missing[0])
            else:
                failures.append(f"{rel} missing strings: {', '.join(missing)}")

    tool_names = [str(t.get("name") or "") for t in tool_calls]
    for needle in checks.get("tool_name_contains", []) or []:
        if not any(_tool_matches_contains(n, str(needle)) for n in tool_names):
            failures.append(f"missing tool call containing: {needle}")

    bash_needles = [str(x) for x in (checks.get("bash_command_contains") or [])]
    if bash_needles:
        bash_commands: List[str] = []
        for t in tool_calls:
            name = str(t.get("name") or "")
            if not _is_bash_tool(name):
                continue
            cmd = _extract_bash_command(t.get("input") or {})
            if cmd:
                bash_commands.append(cmd)

        if not any(any(n in c for n in bash_needles) for c in bash_commands):
            failures.append("missing expected bash command (e.g., unittest run)")

    return len(failures) == 0, failures


def _resolve_repo_paths_for_citations(repo_root: Path) -> List[Path]:
    candidates = [
        repo_root / "regen-ledger",
        repo_root,
        repo_root / "regen-koi-mcp",
        repo_root.parent / "regen-ledger",
        repo_root.parent / "regen-koi-mcp",
    ]
    unique: List[Path] = []
    for c in candidates:
        p = c.resolve()
        if p.exists() and p not in unique:
            unique.append(p)
    return unique


def _run_verify_citations_json(
    *,
    repo_root: Path,
    source_file: Path,
    repo_paths: List[Path],
    scratch_dir: Path,
) -> Dict[str, Any]:
    script_path = (repo_root / "scripts" / "verify-citations.py").resolve()
    repos_arg = ",".join(str(p) for p in repo_paths)
    cmd = [
        sys.executable,
        str(script_path),
        str(source_file),
        "--repos",
        repos_arg,
        "--scratch",
        str(scratch_dir),
        "--format",
        "json",
        "--fail-threshold",
        "1.0",
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    stdout = (proc.stdout or "").strip()
    if not stdout:
        raise RuntimeError(f"verify-citations produced no JSON output (exit={proc.returncode}): {proc.stderr[-500:]}")
    try:
        data = json.loads(stdout)
    except Exception as e:
        raise RuntimeError(f"verify-citations returned invalid JSON (exit={proc.returncode}): {stdout[:500]}") from e

    data["_exit_code"] = proc.returncode
    if proc.stderr:
        data["_stderr_tail"] = (proc.stderr.splitlines() or [])[-50:]
    return data


def _citation_summary(verification: Dict[str, Any]) -> Dict[str, Any]:
    total = int(verification.get("total_citations") or 0)
    verified = int(verification.get("verified_count") or 0)
    failed = int(verification.get("failed_count") or 0)
    skipped = int(verification.get("skipped_count") or 0)
    verifiable = verified + failed
    verified_rate = (verified / verifiable) if verifiable else 0.0
    hallucination_rate = (failed / verifiable) if verifiable else 0.0
    return {
        "total_citations": total,
        "verifiable_citations": verifiable,
        "verified_count": verified,
        "failed_count": failed,
        "skipped_count": skipped,
        "verified_rate": round(verified_rate, 6),
        "hallucination_rate": round(hallucination_rate, 6),
    }


def _aggregate_citations(per_file: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = sum(int(x.get("total_citations") or 0) for x in per_file)
    verified = sum(int(x.get("verified_count") or 0) for x in per_file)
    failed = sum(int(x.get("failed_count") or 0) for x in per_file)
    skipped = sum(int(x.get("skipped_count") or 0) for x in per_file)
    verifiable = verified + failed
    verified_rate = (verified / verifiable) if verifiable else 0.0
    hallucination_rate = (failed / verifiable) if verifiable else 0.0
    return {
        "total_citations": total,
        "verifiable_citations": verifiable,
        "verified_count": verified,
        "failed_count": failed,
        "skipped_count": skipped,
        "verified_rate": round(verified_rate, 6),
        "hallucination_rate": round(hallucination_rate, 6),
    }


def _count_tool_calls(tool_call_names: List[str], needle: str) -> int:
    return sum(1 for n in tool_call_names if _tool_matches_contains(n, needle))


async def _run_suite(
    *,
    scenarios: List[Dict[str, Any]],
    repo_root: Path,
    env_name: str,
    model: str,
    koi_api_endpoint: str,
) -> Dict[str, Any]:
    run_id = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{_rand_suffix()}"
    generated_at = _now_iso()

    run_payload: Dict[str, Any] = {
        "suite": "suite_d",
        "env": env_name,
        "generated_at": generated_at,
        "run_id": run_id,
        "model": model,
        "koi_api_endpoint": koi_api_endpoint,
        "scenarios": [],
    }

    passed = 0
    failed = 0

    for sc in scenarios:
        sc_id = sc.get("id") or "<missing-id>"
        sc_name = sc.get("name") or sc_id
        sc_prompt = sc.get("prompt") or ""

        per_run_id = f"{run_id}-{sc_id}"
        vars_map = {"RUN_ID": per_run_id}
        prompt = _substitute(sc_prompt, vars_map)

        # Enable MCP if the scenario expects MCP tool usage.
        checks = sc.get("checks") or {}
        explicit = sc.get("enable_mcp")
        if isinstance(explicit, bool):
            enable_mcp = explicit
        else:
            enable_mcp = bool(checks.get("tool_name_contains"))

        stderr_lines: List[str] = []
        started = time.time()
        try:
            sdk_result = await _run_prompt_with_sdk(
                prompt,
                cwd=repo_root,
                model=model,
                koi_api_endpoint=koi_api_endpoint,
                enable_mcp=enable_mcp,
                stderr_lines=stderr_lines,
            )
            tool_calls = sdk_result["tool_calls"]
            tool_results = sdk_result["tool_results"]
            assistant_text = sdk_result["assistant_text"]
            result_message = sdk_result["result"]
        except Exception as e:
            duration_ms = int((time.time() - started) * 1000)
            failed += 1
            run_payload["scenarios"].append(
                {
                    "id": sc_id,
                    "name": sc_name,
                    "run_id": per_run_id,
                    "passed": False,
                    "duration_ms": duration_ms,
                    "failures": [f"sdk_error: {e}"],
                    "tool_calls": [],
                    "tool_error_count": 0,
                    "assistant_text": "",
                    "stderr": stderr_lines[-200:],
                    "result": {},
                }
            )
            continue

        duration_ms = int((time.time() - started) * 1000)

        ok, failures = _evaluate_checks(sc, repo_root=repo_root, variables=vars_map, tool_calls=tool_calls)
        tool_error_count = sum(1 for r in tool_results if r.get("is_error") is True)

        if ok:
            passed += 1
        else:
            failed += 1

        run_payload["scenarios"].append(
            {
                "id": sc_id,
                "name": sc_name,
                "run_id": per_run_id,
                "passed": ok,
                "duration_ms": duration_ms,
                "failures": failures,
                "tool_calls": [t.get("name") for t in tool_calls],
                "tool_error_count": tool_error_count,
                "assistant_text": assistant_text,
                "stderr": stderr_lines[-200:],
                "result": result_message,
            }
        )

    run_payload["summary"] = {"total": len(scenarios), "passed": passed, "failed": failed}
    return run_payload


def _traffic_light_from_thresholds(
    *,
    baseline: Dict[str, Any],
    koi: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> Tuple[str, str, Dict[str, Any]]:
    if not baseline.get("passed", False):
        return "red", "baseline_failed_checks", {}
    if not koi.get("passed", False):
        return "red", "koi_failed_checks", {}

    base_cit = baseline.get("citations") or {}
    koi_cit = koi.get("citations") or {}

    min_verifiable = int(thresholds.get("min_koi_verifiable_citations") or 0)
    max_halluc = float(thresholds.get("max_koi_hallucination_rate") or 1.0)
    delta_yellow = float(thresholds.get("min_verified_rate_delta_yellow") or -1.0)
    delta_red = float(thresholds.get("min_verified_rate_delta_red") or -1.0)

    koi_verifiable = int(koi_cit.get("verifiable_citations") or 0)
    koi_halluc = float(koi_cit.get("hallucination_rate") or 0.0)
    if min_verifiable and koi_verifiable < min_verifiable:
        return "red", f"koi_verifiable_citations<{min_verifiable}", {}
    if koi_halluc > max_halluc:
        return "red", f"koi_hallucination_rate>{max_halluc:.2f}", {}

    base_verified_rate = float(base_cit.get("verified_rate") or 0.0)
    koi_verified_rate = float(koi_cit.get("verified_rate") or 0.0)
    verified_rate_delta = koi_verified_rate - base_verified_rate

    base_total = int(base_cit.get("total_citations") or 0)
    koi_total = int(koi_cit.get("total_citations") or 0)
    citations_total_delta = koi_total - base_total

    base_halluc = float(base_cit.get("hallucination_rate") or 0.0)
    hallucination_rate_delta = koi_halluc - base_halluc

    base_tool_calls = int(baseline.get("tool_calls_total") or 0)
    koi_tool_calls = int(koi.get("tool_calls_total") or 0)
    tool_calls_total_delta = koi_tool_calls - base_tool_calls

    base_verifiable = int(base_cit.get("verifiable_citations") or 0)
    verifiable_citations_delta = koi_verifiable - base_verifiable

    base_duration = int(baseline.get("duration_ms") or 0)
    koi_duration = int(koi.get("duration_ms") or 0)
    duration_ms_delta = koi_duration - base_duration

    delta_payload = {
        "citations_total_delta": citations_total_delta,
        "verifiable_citations_delta": verifiable_citations_delta,
        "verified_rate_delta": round(verified_rate_delta, 6),
        "hallucination_rate_delta": round(hallucination_rate_delta, 6),
        "tool_calls_total_delta": tool_calls_total_delta,
        "duration_ms_delta": duration_ms_delta,
    }

    if verified_rate_delta < delta_red:
        return "red", f"verified_rate_delta<{delta_red:.2f}", delta_payload
    if verified_rate_delta < delta_yellow:
        return "yellow", f"verified_rate_delta<{delta_yellow:.2f}", delta_payload

    return "green", "within thresholds", delta_payload


async def _run_delta_variant(
    *,
    variant_name: str,
    pair: Dict[str, Any],
    variant: Dict[str, Any],
    repo_root: Path,
    env_name: str,
    model: str,
    koi_api_endpoint: str,
    repo_paths_for_citations: List[Path],
    scratch_dir: Path,
    run_id: str,
) -> Dict[str, Any]:
    prompt_template = str(pair.get("prompt") or "")
    artifact_paths = pair.get("artifact_paths") or []

    per_run_id = f"{run_id}-{pair.get('id')}-{variant_name}"
    vars_map = {"RUN_ID": per_run_id}
    prompt = _substitute(prompt_template, vars_map)

    enable_mcp = bool(variant.get("enable_mcp") is True)
    checks = variant.get("checks") or {}
    stderr_lines: List[str] = []

    started = time.time()
    try:
        sdk_result = await _run_prompt_with_sdk(
            prompt,
            cwd=repo_root,
            model=model,
            koi_api_endpoint=koi_api_endpoint,
            enable_mcp=enable_mcp,
            stderr_lines=stderr_lines,
        )
        tool_calls = sdk_result["tool_calls"]
        tool_results = sdk_result["tool_results"]
        assistant_text = sdk_result["assistant_text"]
        result_message = sdk_result["result"]
    except Exception as e:
        duration_ms = int((time.time() - started) * 1000)
        return {
            "variant": variant_name,
            "run_id": per_run_id,
            "passed": False,
            "duration_ms": duration_ms,
            "failures": [f"sdk_error: {e}"],
            "tool_calls": [],
            "tool_calls_total": 0,
            "tool_error_count": 0,
            "assistant_text": "",
            "stderr": stderr_lines[-200:],
            "result": {},
            "citations": {},
            "citations_files": [],
        }

    duration_ms = int((time.time() - started) * 1000)

    ok, failures = _evaluate_checks({"checks": checks}, repo_root=repo_root, variables=vars_map, tool_calls=tool_calls)
    tool_error_count = sum(1 for r in tool_results if r.get("is_error") is True)
    tool_call_names = [str(t.get("name") or "") for t in tool_calls]

    # Citation verification (aggregate across artifact files)
    per_file: List[Dict[str, Any]] = []
    citation_errors: List[str] = []
    for p in artifact_paths:
        if not isinstance(p, str):
            continue
        rel = _substitute(p, vars_map)
        abs_path = (repo_root / rel).resolve()
        if not abs_path.exists() or not abs_path.is_file():
            citation_errors.append(f"missing artifact file for citations: {rel}")
            continue
        try:
            verification = _run_verify_citations_json(
                repo_root=repo_root,
                source_file=abs_path,
                repo_paths=repo_paths_for_citations,
                scratch_dir=scratch_dir,
            )
            summary = _citation_summary(verification)
            summary["source_file"] = rel
            per_file.append(summary)
        except Exception as e:
            citation_errors.append(f"citation_verification_error ({rel}): {e}")

    citations = _aggregate_citations(per_file) if per_file else {}
    if citation_errors:
        citations["errors"] = citation_errors

    return {
        "variant": variant_name,
        "run_id": per_run_id,
        "passed": ok,
        "duration_ms": duration_ms,
        "failures": failures,
        "tool_calls": tool_call_names,
        "tool_calls_total": len(tool_call_names),
        "tool_error_count": tool_error_count,
        "assistant_text": assistant_text,
        "stderr": stderr_lines[-200:],
        "result": result_message,
        "citations": citations,
        "citations_files": per_file,
        "koi_tool_calls": {
            "search": _count_tool_calls(tool_call_names, "search"),
            "query_code_graph": _count_tool_calls(tool_call_names, "query_code_graph"),
        },
    }


async def _run_delta_suite(
    *,
    pairs: List[Dict[str, Any]],
    thresholds: Dict[str, Any],
    repo_root: Path,
    env_name: str,
    model: str,
    koi_api_endpoint: str,
) -> Dict[str, Any]:
    run_id = f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{_rand_suffix()}"
    generated_at = _now_iso()

    repo_paths_for_citations = _resolve_repo_paths_for_citations(repo_root)
    scratch_dir = (repo_root / "scratch").resolve()

    run_payload: Dict[str, Any] = {
        "suite": "suite_d_delta",
        "env": env_name,
        "generated_at": generated_at,
        "run_id": run_id,
        "model": model,
        "koi_api_endpoint": koi_api_endpoint,
        "thresholds": thresholds,
        "pairs": [],
    }

    counts = {"green": 0, "yellow": 0, "red": 0}
    verified_rate_deltas: List[float] = []
    citations_deltas: List[int] = []

    for pair in pairs:
        pair_id = pair.get("id") or "<missing-id>"
        pair_name = pair.get("name") or pair_id

        baseline_spec = pair.get("baseline") or {}
        koi_spec = pair.get("koi") or {}

        baseline = await _run_delta_variant(
            variant_name="baseline",
            pair=pair,
            variant=baseline_spec,
            repo_root=repo_root,
            env_name=env_name,
            model=model,
            koi_api_endpoint=koi_api_endpoint,
            repo_paths_for_citations=repo_paths_for_citations,
            scratch_dir=scratch_dir,
            run_id=run_id,
        )
        koi = await _run_delta_variant(
            variant_name="koi",
            pair=pair,
            variant=koi_spec,
            repo_root=repo_root,
            env_name=env_name,
            model=model,
            koi_api_endpoint=koi_api_endpoint,
            repo_paths_for_citations=repo_paths_for_citations,
            scratch_dir=scratch_dir,
            run_id=run_id,
        )

        status, reason, delta_payload = _traffic_light_from_thresholds(baseline=baseline, koi=koi, thresholds=thresholds)
        counts[status] = counts.get(status, 0) + 1

        # Track averages only when deltas exist.
        if "verified_rate_delta" in delta_payload:
            verified_rate_deltas.append(float(delta_payload["verified_rate_delta"]))
        if "citations_total_delta" in delta_payload:
            citations_deltas.append(int(delta_payload["citations_total_delta"]))

        run_payload["pairs"].append(
            {
                "id": pair_id,
                "name": pair_name,
                "status": status,
                "reason": reason,
                "baseline": baseline,
                "koi": koi,
                "delta": delta_payload,
            }
        )

    overall = "green"
    if counts.get("red", 0) > 0:
        overall = "red"
    elif counts.get("yellow", 0) > 0:
        overall = "yellow"

    summary: Dict[str, Any] = {
        "status": overall,
        "total_pairs": len(pairs),
        "green": counts.get("green", 0),
        "yellow": counts.get("yellow", 0),
        "red": counts.get("red", 0),
        "avg_verified_rate_delta": (sum(verified_rate_deltas) / len(verified_rate_deltas)) if verified_rate_deltas else None,
        "avg_citations_delta": (sum(citations_deltas) / len(citations_deltas)) if citations_deltas else None,
    }

    run_payload["koi_value_add_delta"] = {"summary": summary}
    return run_payload


async def _main_async(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    gold_path = Path(args.scenarios).resolve()
    data = _read_json(gold_path)
    run: Dict[str, Any]
    if isinstance(data.get("pairs"), list):
        pairs = [p for p in (data.get("pairs") or []) if isinstance(p, dict)]
        if not pairs:
            print(f"No delta pairs found in {gold_path}", file=sys.stderr)
            return 2
        thresholds = data.get("thresholds") or {}
        run = await _run_delta_suite(
            pairs=pairs,
            thresholds=thresholds if isinstance(thresholds, dict) else {},
            repo_root=repo_root,
            env_name=args.env,
            model=args.model,
            koi_api_endpoint=args.koi_api_endpoint,
        )
    else:
        scenarios = data.get("scenarios") or []
        if not isinstance(scenarios, list) or not scenarios:
            print(f"No scenarios found in {gold_path}", file=sys.stderr)
            return 2

        run = await _run_suite(
            scenarios=[s for s in scenarios if isinstance(s, dict)],
            repo_root=repo_root,
            env_name=args.env,
            model=args.model,
            koi_api_endpoint=args.koi_api_endpoint,
        )

    if args.out_json:
        _write_json(Path(args.out_json), run)

    md = _render_md_report(run)
    if args.out_md:
        _write_text(Path(args.out_md), md)

    # Exit non-zero if any scenario failed.
    if run.get("suite") == "suite_d_delta":
        status = ((run.get("koi_value_add_delta") or {}).get("summary") or {}).get("status") or "unknown"
        if status == "red":
            return 1
        return 0

    if (run.get("summary") or {}).get("failed", 0) > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Suite D agent scenarios via Claude Agent SDK.")
    parser.add_argument("--env", default="prod", help="Environment label for reports (default: prod)")
    parser.add_argument("--model", default=os.environ.get("MODEL", "sonnet"), help="Model name (e.g., sonnet/opus)")
    parser.add_argument(
        "--koi-api-endpoint",
        default=os.environ.get("KOI_API_ENDPOINT", "https://regen.gaiaai.xyz/api/koi"),
        help="KOI API endpoint for MCP server (default: env KOI_API_ENDPOINT or prod)",
    )
    parser.add_argument("--scenarios", default="evals/suite_d_scenarios.json", help="Path to Suite D scenarios JSON")
    parser.add_argument("--repo-root", default=".", help="Repo root / working directory for Claude Code")
    parser.add_argument("--out-json", default="", help="Write Suite D JSON report to this path")
    parser.add_argument("--out-md", default="", help="Write Suite D Markdown report to this path")
    args = parser.parse_args()

    try:
        import anyio  # type: ignore
    except Exception:
        print("anyio is required (install via: python3 -m pip install claude-agent-sdk)", file=sys.stderr)
        return 2

    try:
        import claude_agent_sdk  # noqa: F401
    except Exception:
        print(
            "Claude Agent SDK is required (install via: python3 -m pip install claude-agent-sdk)",
            file=sys.stderr,
        )
        return 2

    return anyio.run(_main_async, args)


if __name__ == "__main__":
    raise SystemExit(main())
