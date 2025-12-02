# MEVSCOPE — Architecture

> Replays a tx or address history to attribute sandwich, frontrun, and backrun MEV extraction with per-trade loss accounting.

```
input ──▶ collect ──▶ rules/analyzers ──▶ score ──▶ findings ──▶ table · json
                              │                          │
                         (this repo)                 MCP tool (agents)
```

- **collect** normalizes the target (file/dir/API) into records.
- **rules/analyzers** apply the heuristics shipped in `mevscope/core.py`.
- **score** ranks by severity.
- **MCP server** (`mevscope mcp`) exposes `scan` for Cognis.Studio agents.

Extend by adding a rule + a test + a `demos/NN-*/SCENARIO.md`. See [CONTRIBUTING.md](../CONTRIBUTING.md).
