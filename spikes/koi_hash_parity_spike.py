#!/usr/bin/env python3
"""Hash parity spike for KOI protocol alignment.

Compares RegenAI's current hashing (json.dumps(sort_keys=True)) against a
JCS-style canonicalization hash (rid-lib vendor canonicalize, and optionally
canonicaljson if installed).

This is research-only and should not modify repo code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regen_legacy_bytes(obj: Any) -> bytes:
    """Match current koi-sensors Manifest.generate() behavior."""
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, sort_keys=True).encode("utf-8")
    if isinstance(obj, str):
        return obj.encode("utf-8")
    return str(obj).encode("utf-8")


def regen_compact_bytes(obj: Any) -> bytes:
    """A closer-to-canonical JSON encoding (not currently used in RegenAI)."""
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if isinstance(obj, str):
        return obj.encode("utf-8")
    return str(obj).encode("utf-8")


def _try_load_ridlib_canonicalize(repo_root: Path):
    ridlib_src = repo_root / "koi-research" / "sources" / "blockscience" / "rid-lib" / "src"
    if ridlib_src.exists():
        sys.path.insert(0, str(ridlib_src))
    try:
        from rid_lib._vendor.org.webpki.json.Canonicalize import canonicalize  # type: ignore
    except Exception:
        return None
    return canonicalize


def canonical_bytes(obj: Any, repo_root: Path) -> Tuple[str, bytes]:
    """Return (engine, canonical_bytes) using canonicaljson if present, else rid-lib vendor."""
    try:
        import canonicaljson  # type: ignore

        return "canonicaljson", canonicaljson.canonicalize(obj)
    except Exception:
        pass

    canonicalize = _try_load_ridlib_canonicalize(repo_root)
    if canonicalize is None:
        # Last-resort fallback (NOT JCS): compact JSON without ASCII escapes.
        return "json_compact_fallback", regen_compact_bytes(obj)

    canon = canonicalize(obj, utf8=True)
    if isinstance(canon, bytes):
        return "rid-lib.vendor.JCS", canon
    return "rid-lib.vendor.JCS", str(canon).encode("utf-8")


@dataclass(frozen=True)
class PayloadRecord:
    source: str
    kind: str
    payload: Any
    manifest_hash: Optional[str] = None


def iter_json_files(paths: Sequence[Path]) -> Iterator[Path]:
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".json":
            yield p
        elif p.is_dir():
            yield from (f for f in p.rglob("*.json") if f.is_file())


def _safe_json_load(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extract_payloads_from_json(path: Path, data: Any) -> List[PayloadRecord]:
    records: List[PayloadRecord] = []

    # Coordinator queue shape
    if isinstance(data, dict) and isinstance(data.get("events"), list) and all(isinstance(e, dict) for e in data["events"]):
        # Heuristic: look for nested event.bundle.contents
        for idx, item in enumerate(data["events"]):
            event = item.get("event") if isinstance(item, dict) else None
            if not isinstance(event, dict):
                continue
            bundle = event.get("bundle")
            if isinstance(bundle, dict) and "contents" in bundle:
                manifest_hash = None
                manifest = bundle.get("manifest")
                if isinstance(manifest, dict):
                    manifest_hash = manifest.get("content_hash") or manifest.get("sha256_hash")
                records.append(
                    PayloadRecord(
                        source=str(path),
                        kind=f"coordinator_queue_event[{idx}].bundle.contents",
                        payload=bundle.get("contents"),
                        manifest_hash=manifest_hash,
                    )
                )
        if records:
            return records

    # Discourse-like output shape
    if isinstance(data, dict) and isinstance(data.get("documents"), list):
        for idx, doc in enumerate(data["documents"]):
            if isinstance(doc, (dict, list, str)):
                doc_id = doc.get("id") if isinstance(doc, dict) else None
                kind = f"documents[{idx}]" + (f" id={doc_id}" if doc_id else "")
                records.append(PayloadRecord(source=str(path), kind=kind, payload=doc))
        if records:
            return records

    # Twitter-like output shape
    if isinstance(data, dict) and isinstance(data.get("tweets"), list):
        for idx, tweet in enumerate(data["tweets"]):
            if isinstance(tweet, (dict, list, str)):
                kind = f"tweets[{idx}]"
                records.append(PayloadRecord(source=str(path), kind=kind, payload=tweet))
        if records:
            return records

    # Generic list payload
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, (dict, list, str)):
                kind = f"list[{idx}]"
                records.append(PayloadRecord(source=str(path), kind=kind, payload=item))
        if records:
            return records

    # Fallback: treat whole document as payload
    records.append(PayloadRecord(source=str(path), kind="root", payload=data))
    return records


@dataclass
class HashResult:
    record: PayloadRecord
    legacy_hash: str
    compact_hash: str
    canonical_engine: str
    canonical_hash: str
    legacy_matches_canonical: bool
    compact_matches_canonical: bool
    manifest_matches_legacy: Optional[bool]


def compute_hashes(records: Sequence[PayloadRecord], repo_root: Path) -> List[HashResult]:
    results: List[HashResult] = []
    for rec in records:
        legacy_bytes = regen_legacy_bytes(rec.payload)
        compact_bytes = regen_compact_bytes(rec.payload)
        engine, canon_bytes = canonical_bytes(rec.payload, repo_root)

        legacy_hash = _sha256_hex(legacy_bytes)
        compact_hash = _sha256_hex(compact_bytes)
        canon_hash = _sha256_hex(canon_bytes)

        manifest_ok: Optional[bool] = None
        if rec.manifest_hash:
            manifest_ok = (rec.manifest_hash == legacy_hash)

        results.append(
            HashResult(
                record=rec,
                legacy_hash=legacy_hash,
                compact_hash=compact_hash,
                canonical_engine=engine,
                canonical_hash=canon_hash,
                legacy_matches_canonical=(legacy_hash == canon_hash),
                compact_matches_canonical=(compact_hash == canon_hash),
                manifest_matches_legacy=manifest_ok,
            )
        )
    return results


def summarize(results: Sequence[HashResult]) -> dict:
    total = len(results)
    legacy_mismatch = sum(1 for r in results if not r.legacy_matches_canonical)
    compact_mismatch = sum(1 for r in results if not r.compact_matches_canonical)
    manifest_checked = [r for r in results if r.manifest_matches_legacy is not None]
    manifest_mismatch = sum(1 for r in manifest_checked if r.manifest_matches_legacy is False)

    by_engine: dict[str, int] = {}
    for r in results:
        by_engine[r.canonical_engine] = by_engine.get(r.canonical_engine, 0) + 1

    return {
        "total_payloads": total,
        "legacy_mismatch_count": legacy_mismatch,
        "legacy_mismatch_pct": (legacy_mismatch / total * 100) if total else 0.0,
        "compact_mismatch_count": compact_mismatch,
        "compact_mismatch_pct": (compact_mismatch / total * 100) if total else 0.0,
        "manifest_checked": len(manifest_checked),
        "manifest_mismatch_count": manifest_mismatch,
        "canonical_engine_counts": by_engine,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="KOI hash parity spike")
    parser.add_argument(
        "--repo-root",
        default=os.getcwd(),
        help="Repo root (default: cwd)",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="File or directory to scan (repeatable)",
    )
    parser.add_argument(
        "--max-payloads",
        type=int,
        default=2000,
        help="Cap total payloads processed (default: 2000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for sampling (default: 1337)",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=10,
        help="Number of mismatching examples to print (default: 10)",
    )

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    default_paths = [
        repo_root / "koi-sensors" / "koi_protocol" / "coordinator" / "coordinator_event_queue.json",
        repo_root / "koi-sensors" / "sensors" / "discourse" / "output",
        repo_root / "koi-sensors" / "sensors" / "telegram" / "output",
        repo_root / "koi-sensors" / "sensors" / "twitter" / "output",
        repo_root / "koi-sensors" / "sensors" / "medium" / "medium_articles_test.json",
        repo_root / "koi-sensors" / "sensors" / "podcast" / "transcripts",
    ]

    scan_paths = [Path(p).resolve() for p in args.path] if args.path else default_paths

    json_files = sorted(set(iter_json_files(scan_paths)))

    random.seed(args.seed)

    all_records: List[PayloadRecord] = []
    for jf in json_files:
        data = _safe_json_load(jf)
        if data is None:
            continue
        records = extract_payloads_from_json(jf, data)
        all_records.extend(records)

    if len(all_records) > args.max_payloads:
        all_records = random.sample(all_records, args.max_payloads)

    results = compute_hashes(all_records, repo_root)
    summary = summarize(results)

    print("# KOI Hash Parity Spike")
    print()
    print("## Environment")
    print(f"- repo_root: {repo_root}")
    print(f"- python: {sys.version.split()[0]}")

    # Dependency presence checks
    try:
        import rid_lib  # type: ignore
        rid_lib_installed = True
    except Exception:
        rid_lib_installed = False
    try:
        import canonicaljson  # type: ignore
        canonicaljson_installed = True
    except Exception:
        canonicaljson_installed = False

    print(f"- rid_lib installed: {rid_lib_installed}")
    print(f"- canonicaljson installed: {canonicaljson_installed}")

    print()
    print("## Summary")
    for k, v in summary.items():
        print(f"- {k}: {v}")

    print()
    print("## Examples (legacy != canonical)")
    examples = [r for r in results if not r.legacy_matches_canonical]
    for r in examples[: max(args.examples, 0)]:
        rec = r.record
        print("-")
        print(f"  - source: {rec.source}")
        print(f"  - kind: {rec.kind}")
        if rec.manifest_hash:
            print(f"  - manifest_hash: {rec.manifest_hash}")
            print(f"  - manifest_matches_legacy: {r.manifest_matches_legacy}")
        print(f"  - legacy_hash: {r.legacy_hash}")
        print(f"  - compact_hash: {r.compact_hash}")
        print(f"  - canonical_engine: {r.canonical_engine}")
        print(f"  - canonical_hash: {r.canonical_hash}")
        print(f"  - compact_matches_canonical: {r.compact_matches_canonical}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
