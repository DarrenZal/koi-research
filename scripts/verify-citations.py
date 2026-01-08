#!/usr/bin/env python3
"""
Hallucination Detection: Verify agent citations against actual repos.

Extracts file paths, line numbers, and symbols from agent output,
then verifies they actually exist. Reports hallucination rate.

Usage:
    # Verify a single markdown file (test results)
    python scripts/verify-citations.py docs/test-results/2026-01-08-dogfood.md

    # Verify with specific repo paths
    python scripts/verify-citations.py results.md --repos /path/to/regen-ledger,/path/to/regen-web

    # Output JSON for CI integration
    python scripts/verify-citations.py results.md --format json

    # Use KOI API to verify symbols (requires network)
    python scripts/verify-citations.py results.md --use-koi-api

Exit codes:
    0 = All citations verified (or no citations found)
    1 = Some citations failed verification
    2 = Error (file not found, network error, etc.)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

# ============================================
# Citation extraction patterns
# ============================================

# File paths: src/foo/bar.ts, x/ecocredit/tx.pb.go, etc.
FILE_PATH_PATTERN = re.compile(
    r'(?:^|[\s`\[\(])('
    r'(?:src|x|app|pkg|internal|lib|scripts|docs|evals)/'  # common prefixes
    r'[a-zA-Z0-9_/.-]+'
    r'\.(?:go|ts|tsx|js|jsx|rs|py|md|json|yaml|yml|proto|sql)'
    r')(?:$|[\s`\]\),:;])',
    re.MULTILINE
)

# File:line references: tx.pb.go:35, contract.rs:123
FILE_LINE_PATTERN = re.compile(
    r'([a-zA-Z0-9_.-]+\.(?:go|ts|tsx|js|jsx|rs|py|md|proto))'
    r':(\d+)'
)

# GitHub URLs: github.com/org/repo/blob/branch/path/file.go
GITHUB_URL_PATTERN = re.compile(
    r'https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/([^\s\)]+)'
)

# Symbol references: MsgCreateBatch, QueryBasketRequest, etc.
# Look for PascalCase identifiers that look like Go/Rust types or protobuf messages
SYMBOL_PATTERN = re.compile(
    r'(?:^|[\s`\[\(])'
    r'((?:Msg|Query|Keeper|Handler|Request|Response|State|Config|Params)[A-Z][a-zA-Z0-9]*)'
    r'(?:$|[\s`\]\),:;])'
)

# Code block extraction
CODE_BLOCK_PATTERN = re.compile(r'```(?:\w+)?\n(.*?)```', re.DOTALL)


@dataclass
class Citation:
    """A single citation extracted from agent output."""
    type: str  # 'file_path', 'file_line', 'github_url', 'symbol'
    raw: str   # Original text matched
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    symbol: Optional[str] = None
    repo: Optional[str] = None
    verified: Optional[bool] = None
    error: Optional[str] = None
    context: Optional[str] = None  # Surrounding text for debugging


@dataclass
class VerificationResult:
    """Results of verifying all citations in a document."""
    source_file: str
    total_citations: int = 0
    verified_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    hallucination_rate: float = 0.0
    citations: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def to_dict(self):
        return {
            'source_file': self.source_file,
            'total_citations': self.total_citations,
            'verified_count': self.verified_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'hallucination_rate': self.hallucination_rate,
            'citations': [asdict(c) for c in self.citations],
            'errors': self.errors,
        }


# ============================================
# Citation extraction
# ============================================

def extract_citations(text: str) -> list[Citation]:
    """Extract all citations from markdown/text content."""
    citations = []

    # Extract file paths
    for match in FILE_PATH_PATTERN.finditer(text):
        path = match.group(1)
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        citations.append(Citation(
            type='file_path',
            raw=path,
            file_path=path,
            context=text[start:end].strip()
        ))

    # Extract file:line references
    for match in FILE_LINE_PATTERN.finditer(text):
        filename = match.group(1)
        line = int(match.group(2))
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        citations.append(Citation(
            type='file_line',
            raw=f"{filename}:{line}",
            file_path=filename,
            line_number=line,
            context=text[start:end].strip()
        ))

    # Extract GitHub URLs
    for match in GITHUB_URL_PATTERN.finditer(text):
        org, repo, branch, path = match.groups()
        citations.append(Citation(
            type='github_url',
            raw=match.group(0),
            file_path=path,
            repo=f"{org}/{repo}",
            context=match.group(0)
        ))

    # Extract symbols (deduplicated)
    seen_symbols = set()
    for match in SYMBOL_PATTERN.finditer(text):
        symbol = match.group(1)
        if symbol not in seen_symbols:
            seen_symbols.add(symbol)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            citations.append(Citation(
                type='symbol',
                raw=symbol,
                symbol=symbol,
                context=text[start:end].strip()
            ))

    return citations


# ============================================
# Verification methods
# ============================================

def find_file_in_repos(filename: str, repo_paths: list[Path]) -> Optional[Path]:
    """Search for a file across multiple repo paths."""
    for repo_path in repo_paths:
        # Try exact path first
        exact = repo_path / filename
        if exact.exists():
            return exact

        # Try finding by filename anywhere in repo
        try:
            result = subprocess.run(
                ['find', str(repo_path), '-name', Path(filename).name, '-type', 'f'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                found = result.stdout.strip().split('\n')[0]
                return Path(found)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return None


def verify_file_exists(citation: Citation, repo_paths: list[Path]) -> Citation:
    """Verify a file path citation exists."""
    if not citation.file_path:
        citation.verified = False
        citation.error = "No file path to verify"
        return citation

    found = find_file_in_repos(citation.file_path, repo_paths)
    if found:
        citation.verified = True

        # If line number specified, verify it's in range
        if citation.line_number:
            try:
                with open(found, 'r') as f:
                    lines = f.readlines()
                if citation.line_number <= len(lines):
                    citation.verified = True
                else:
                    citation.verified = False
                    citation.error = f"Line {citation.line_number} exceeds file length ({len(lines)} lines)"
            except Exception as e:
                citation.error = f"Could not read file: {e}"
    else:
        citation.verified = False
        citation.error = f"File not found in any repo: {citation.file_path}"

    return citation


def verify_symbol_via_grep(citation: Citation, repo_paths: list[Path]) -> Citation:
    """Verify a symbol exists by grepping repos."""
    if not citation.symbol:
        citation.verified = False
        citation.error = "No symbol to verify"
        return citation

    for repo_path in repo_paths:
        try:
            result = subprocess.run(
                ['grep', '-r', '-l', citation.symbol, str(repo_path),
                 '--include=*.go', '--include=*.ts', '--include=*.rs', '--include=*.proto'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                citation.verified = True
                return citation
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    citation.verified = False
    citation.error = f"Symbol not found in any repo: {citation.symbol}"
    return citation


def verify_symbol_via_koi_api(citation: Citation, api_endpoint: str) -> Citation:
    """Verify a symbol exists via KOI query_code_graph API."""
    if not citation.symbol:
        citation.verified = False
        citation.error = "No symbol to verify"
        return citation

    try:
        url = f"{api_endpoint.rstrip('/')}/graph"
        payload = json.dumps({
            "query_type": "search_entities",
            "entity_name": citation.symbol,
            "limit": 5
        }).encode('utf-8')

        req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

            results = data.get('data', {}).get('results', [])
            if results:
                citation.verified = True
                # Add context about where it was found
                first_result = results[0]
                citation.context = f"Found in: {first_result.get('file_path', 'unknown')}"
            else:
                citation.verified = False
                citation.error = f"Symbol not found in KOI index: {citation.symbol}"

    except URLError as e:
        citation.verified = None  # Skip, don't count as failure
        citation.error = f"KOI API error: {e}"
    except Exception as e:
        citation.verified = None
        citation.error = f"Verification error: {e}"

    return citation


def verify_github_url(citation: Citation) -> Citation:
    """Verify a GitHub URL is accessible (HEAD request)."""
    if not citation.raw:
        citation.verified = False
        citation.error = "No URL to verify"
        return citation

    # Convert blob URL to raw URL for checking
    raw_url = citation.raw.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')

    try:
        req = Request(raw_url, method='HEAD')
        with urlopen(req, timeout=10) as response:
            if response.status == 200:
                citation.verified = True
            else:
                citation.verified = False
                citation.error = f"GitHub returned status {response.status}"
    except URLError as e:
        citation.verified = False
        citation.error = f"GitHub URL not accessible: {e}"
    except Exception as e:
        citation.verified = False
        citation.error = f"Verification error: {e}"

    return citation


# ============================================
# Main verification logic
# ============================================

def verify_citations(
    text: str,
    source_file: str,
    repo_paths: list[Path],
    use_koi_api: bool = False,
    koi_api_endpoint: str = "https://regen.gaiaai.xyz/api/koi"
) -> VerificationResult:
    """Extract and verify all citations in a document."""

    result = VerificationResult(source_file=source_file)
    citations = extract_citations(text)
    result.total_citations = len(citations)

    for citation in citations:
        if citation.type == 'file_path':
            verify_file_exists(citation, repo_paths)
        elif citation.type == 'file_line':
            verify_file_exists(citation, repo_paths)
        elif citation.type == 'github_url':
            verify_github_url(citation)
        elif citation.type == 'symbol':
            if use_koi_api:
                verify_symbol_via_koi_api(citation, koi_api_endpoint)
            else:
                verify_symbol_via_grep(citation, repo_paths)

        result.citations.append(citation)

        if citation.verified is True:
            result.verified_count += 1
        elif citation.verified is False:
            result.failed_count += 1
        else:
            result.skipped_count += 1

    # Calculate hallucination rate (failed / (verified + failed))
    verifiable = result.verified_count + result.failed_count
    if verifiable > 0:
        result.hallucination_rate = result.failed_count / verifiable

    return result


def print_result(result: VerificationResult, format: str = 'text'):
    """Print verification results."""
    if format == 'json':
        print(json.dumps(result.to_dict(), indent=2))
        return

    print(f"\n{'='*60}")
    print(f"Citation Verification: {result.source_file}")
    print(f"{'='*60}")
    print(f"Total citations found: {result.total_citations}")
    print(f"  Verified: {result.verified_count}")
    print(f"  Failed:   {result.failed_count}")
    print(f"  Skipped:  {result.skipped_count}")
    print(f"Hallucination rate: {result.hallucination_rate:.1%}")
    print()

    if result.failed_count > 0:
        print("FAILED CITATIONS:")
        print("-" * 40)
        for c in result.citations:
            if c.verified is False:
                print(f"  [{c.type}] {c.raw}")
                print(f"    Error: {c.error}")
                print()

    if result.verified_count > 0 and format != 'brief':
        print("VERIFIED CITATIONS:")
        print("-" * 40)
        for c in result.citations:
            if c.verified is True:
                print(f"  [{c.type}] {c.raw}")
        print()


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='Verify agent citations against actual repos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('file', help='Markdown file to verify (test results)')
    parser.add_argument('--repos', help='Comma-separated repo paths to search',
                        default='/workspaces/regen-ledger,/workspaces/koi-research')
    parser.add_argument('--scratch', help='Also search scratch directories for created files',
                        default='scratch')
    parser.add_argument('--format', choices=['text', 'json', 'brief'], default='text',
                        help='Output format')
    parser.add_argument('--use-koi-api', action='store_true',
                        help='Use KOI API to verify symbols (requires network)')
    parser.add_argument('--koi-api-endpoint', default='https://regen.gaiaai.xyz/api/koi',
                        help='KOI API endpoint')
    parser.add_argument('--fail-threshold', type=float, default=0.2,
                        help='Hallucination rate threshold for exit code 1 (default: 0.2 = 20%%)')
    parser.add_argument('--ignore-proposed', action='store_true',
                        help='Ignore citations in code blocks marked as proposals/examples')

    args = parser.parse_args()

    # Read input file
    try:
        with open(args.file, 'r') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    # Parse repo paths
    repo_paths = [Path(p.strip()) for p in args.repos.split(',')]

    # Add scratch directories if specified
    if args.scratch:
        scratch_paths = [Path(p.strip()) for p in args.scratch.split(',')]
        repo_paths.extend(scratch_paths)

    repo_paths = [p for p in repo_paths if p.exists()]

    if not repo_paths:
        print("Warning: No valid repo paths found. Symbol/file verification may fail.", file=sys.stderr)
    else:
        print(f"Searching in: {', '.join(str(p) for p in repo_paths)}", file=sys.stderr)

    # Run verification
    result = verify_citations(
        text=text,
        source_file=args.file,
        repo_paths=repo_paths,
        use_koi_api=args.use_koi_api,
        koi_api_endpoint=args.koi_api_endpoint
    )

    # Output
    print_result(result, args.format)

    # Exit code (send status to stderr if outputting json to keep stdout clean)
    status_out = sys.stderr if args.format == 'json' else sys.stdout
    if result.hallucination_rate > args.fail_threshold:
        print(f"\nFAIL: Hallucination rate {result.hallucination_rate:.1%} exceeds threshold {args.fail_threshold:.1%}", file=status_out)
        sys.exit(1)
    elif result.total_citations == 0:
        print("\nWARN: No citations found to verify", file=status_out)
        sys.exit(0)
    else:
        print(f"\nPASS: Hallucination rate {result.hallucination_rate:.1%} within threshold", file=status_out)
        sys.exit(0)


if __name__ == '__main__':
    main()
