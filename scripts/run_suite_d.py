#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import string
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
        mcp_servers = {
            "regen-koi": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "regen-koi-mcp@latest"],
                "env": {"KOI_API_ENDPOINT": koi_api_endpoint},
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


async def _main_async(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    gold_path = Path(args.scenarios).resolve()
    data = _read_json(gold_path)
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
