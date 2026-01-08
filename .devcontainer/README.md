# Regen Full-Stack Test Environment

This devcontainer provides a complete environment for running the full-stack code generation tests.

## What's Included

| Tool | Version | Purpose |
|------|---------|---------|
| Go | 1.22 | regen-ledger development (NU-01) |
| Rust + wasm32 | stable | CosmWasm contracts (SC-01) |
| Python | 3.x | General scripting (VC-01, CA-01) |
| Node.js | 20 LTS | MCP tools, Claude Code CLI |
| regen-ledger | cloned on create | Used for upgrade handler tests (NU-01) |

## Usage

### VS Code / Cursor

1. Open koi-research folder
2. When prompted, click "Reopen in Container"
3. Wait for container to build (~5 min first time)
4. Container will auto-run `setup-repos` + `verify-env` on first create
5. Re-run `verify-env` any time to confirm tooling

### GitHub Codespaces

1. Go to https://github.com/DarrenZal/koi-research
2. Click "Code" → "Codespaces" → "Create codespace"
3. Environment will be ready in ~5 min

### Docker CLI

```bash
# Build
docker build -t regen-test-env .devcontainer/

# Run interactive
docker run -it -v $(pwd):/workspaces/koi-research regen-test-env

# First-time repo bootstrap + verify
docker run regen-test-env setup-repos
docker run regen-test-env verify-env
```

## Running Tests

Once in the container:

```bash
# Quick environment check
verify-env

# Run test protocol helper
./scripts/run-test-protocol.sh --suite tier1

# Or manually follow the protocol
cat docs/test-protocol-full-stack.md
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `REGEN_LEDGER_PATH` | Path to regen-ledger clone |
| `KOI_RESEARCH_PATH` | Path to this repo |
| `ANTHROPIC_API_KEY` | For Claude Code CLI (set externally) |
| `KOI_AUTH_TOKEN` | For KOI private doc access (set externally) |

## Troubleshooting

### Go tests fail with "module not found"
```bash
cd /workspaces/regen-ledger
go mod download
```

### Rust/Cargo not found
```bash
source $HOME/.cargo/env
```

### MCP tools not available
Ensure Claude Code is configured with the KOI MCP server. Check `~/.claude/config.json`.

## Updating

To update tooling versions, edit `.devcontainer/Dockerfile` and rebuild:

```bash
# VS Code: Cmd+Shift+P → "Dev Containers: Rebuild Container"
# CLI: docker build --no-cache -t regen-test-env .devcontainer/
```
