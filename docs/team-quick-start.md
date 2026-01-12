# Team Quick Start: Full Stack KOI MCP

> Get an AI assistant with full awareness of Regen tech systems in 5 minutes.

---

## 1. Install (30 seconds)

**Claude Code CLI:** (recommended)
```bash
claude mcp add regen-koi npx regen-koi-mcp@latest
```

**Other clients:**
| Client | Install Command |
|--------|-----------------|
| Warp | `/add-mcp regen-koi npx -y regen-koi-mcp@latest` |
| VS Code (Cline/Continue) | Add to MCP config - see [full guide](https://github.com/gaiaaiagent/regen-koi-mcp#manual-configuration-all-clients) |
| Cursor | Add to MCP config |
| Claude Desktop | Add to `claude_desktop_config.json` |

---

## 2. Verify It Works (1 minute)

Start a new Claude Code session and ask:

```
What repositories are indexed in KOI?
```

**Expected:** A list of 8 repositories including `regen-ledger`, `regen-web`, etc.

If you see this, you're ready to go.

---

## 3. Try These Prompts

### Basic knowledge retrieval:
```
What is the Registry Agent? Use KOI search to find documentation.
```

### Code navigation:
```
Use query_code_graph to find the MsgRetire message implementation.
Show me the file path and explain what it does.
```

### Grounded technical brief:
```
Explain how ecocredit baskets work, with code pointers to x/ecocredit/basket.
Include a Sources section citing where you found each piece of information.
```

### On-chain queries (if Ledger MCP installed):
```
What's the current balance in the Regen community pool?
```

---

## 4. Access Private Docs (Optional)

If you have a @regen.network email and want to access internal Notion:

```
Can you authenticate me to access private Regen docs?
```

This opens a browser for Google OAuth. After authenticating, you can search internal documentation.

---

## 5. Report Issues

Found a bug or have feedback?

- **Slack:** Post in the Gaia AI channel
- **GitHub:** https://github.com/gaiaaiagent/regen-koi-mcp/issues

---

## What You're Testing

We want to know:

1. **Does it work?** Can you install and run basic queries?
2. **Is it useful?** Does it answer your real questions about Regen systems?
3. **What's missing?** What did you try that didn't work or wasn't available?

---

## Available Tools

| Tool | What it does | Example |
|------|--------------|---------|
| `search` | Search 48K+ docs (forum, GitHub, Medium, Notion) | "Registry Agent responsibilities" |
| `query_code_graph` | Navigate 31K+ code entities across 8 repos | "Find MsgCreateBatch" |
| `search_github_docs` | Search GitHub READMEs and docs | "validator setup guide" |
| `generate_weekly_digest` | Get ecosystem activity summary | "Generate a digest for last week" |
| `regen_koi_authenticate` | Access private Notion (requires @regen.network) | "Authenticate me" |

---

## Troubleshooting

### "Tool not found" or "MCP not connected"
- Restart Claude Code / your client
- Check install: `claude mcp list` should show `regen-koi`

### "Authentication required"
- Some features (private docs, metrics) need OAuth
- Ask "Can you authenticate me?" to start the flow

### Slow responses
- First query may take 5-10 seconds (cold start)
- Subsequent queries should be faster

---

## More Resources

- **Full User Guide:** [regen-koi-mcp/docs/USER_GUIDE.md](https://github.com/gaiaaiagent/regen-koi-mcp/blob/main/docs/USER_GUIDE.md)
- **Deeper Testing Protocol:** [koi-research/docs/test-protocol-full-stack.md](./test-protocol-full-stack.md)
- **GitHub:** https://github.com/gaiaaiagent/regen-koi-mcp
