<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:6b46c1,100:2b6cb0&height=120&section=header&text=MEVSCOPE&fontSize=48&fontColor=ffffff&fontAlignY=58" width="100%" alt="MEVSCOPE"/>

# MEVSCOPE

### Replays a tx or address history to attribute sandwich, frontrun, and backrun MEV extraction with per-trade loss accounting.

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3500&pause=1000&color=6B46C1&center=true&vCenter=true&width=720&lines=Replays+a+tx+or+address+history+to+attribute+sandwich+frontr;Self-hostable+%C2%B7+MCP-native+%C2%B7+CI-ready+%C2%B7+polyglot" width="720"/>

[![PyPI](https://img.shields.io/pypi/v/cognis-mevscope.svg?color=6b46c1)](https://pypi.org/project/cognis-mevscope/) [![CI](https://github.com/cognis-digital/mevscope/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/mevscope/actions) [![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

*Web3 & Smart-Contract Security — on-chain safety and analytics.*

</div>

```bash
pip install cognis-mevscope
mevscope scan .            # → prioritized findings in seconds
```

## Usage — step by step

`mevscope` replays DEX swap history and attributes sandwich/frontrun MEV with
per-trade victim-loss accounting. Console script: `mevscope` (or `python -m mevscope`).

1. **Install** from a clone:
   ```bash
   pip install -e .
   ```
2. **Scan a swap-history JSON file** for sandwich attacks:
   ```bash
   mevscope scan demos/01-basic/swaps.json
   ```
3. **Read the output** — `--format json` exposes totals you can pipe:
   ```bash
   mevscope scan swaps.json --format json | jq '.total_victim_loss'
   ```
4. **Gate on MEV** — `--fail-on-mev` exits non-zero if any sandwich is detected:
   ```bash
   mevscope scan swaps.json --fail-on-mev
   ```
   Exit codes: `0` clean, `1` sandwich detected with `--fail-on-mev`, `2` input error.
5. **Automate in CI** — flag regressions in a protected-router test fixture:
   ```yaml
   - run: pip install -e .
   - run: mevscope scan fixtures/swaps.json --fail-on-mev
   ```

## Contents

- [Why mevscope?](#why) · [Features](#features) · [Quick start](#quick-start) · [Example](#example) · [Architecture](#architecture) · [AI stack](#ai-stack) · [How it compares](#how-it-compares) · [Integrations](#integrations) · [Install anywhere](#install-anywhere) · [Related](#related) · [Contributing](#contributing)

<a name="why"></a>
## Why mevscope?

'How much was I sandwiched this month?' as a single CLI command — quantified victim losses are intensely shareable on Crypto Twitter.

`mevscope` is single-purpose, scriptable, and self-hostable: point it at a target, get prioritized results in the format your workflow already speaks (table · JSON · SARIF), gate CI on it, and let agents drive it over MCP.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="features"></a>
## Features

- ✅ Load Swaps From Obj
- ✅ Load Swaps
- ✅ Detect Sandwiches
- ✅ Build Report
- ✅ Runs on Linux/macOS/Windows · Docker · devcontainer
- ✅ Ports in Python, JavaScript, Go, and Rust (`ports/`)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="quick-start"></a>
## Quick start

```bash
pip install cognis-mevscope
mevscope --version
mevscope scan .                       # scan current project
mevscope scan . --format json         # machine-readable
mevscope scan . --fail-on high        # CI gate (non-zero exit)
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="example"></a>
## Example

```text
$ mevscope scan .
  [HIGH    ] MEV-001  example finding             (./src/app.py)
  [MEDIUM  ] MEV-002  another signal              (./config.yaml)

  2 findings · risk score 5 · 38ms
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="architecture"></a>
## Architecture

```mermaid
flowchart LR
  IN[input] --> P[mevscope<br/>analyze + score]
  P --> OUT[report]
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="ai-stack"></a>
## Use it from any AI stack

`mevscope` is interoperable with every popular way of using AI:

- **MCP server** — `mevscope mcp` (Claude Desktop, Cursor, Cognis.Studio, [uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet))
- **OpenAI-compatible / JSON** — pipe `mevscope scan . --format json` into any agent or LLM
- **LangChain · CrewAI · AutoGen · LlamaIndex** — wrap the CLI/JSON as a tool in one line
- **CI / scripts** — exit codes + SARIF for non-AI pipelines

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="how-it-compares"></a>
## How it compares

| | **Cognis mevscope** | EigenPhi |
|---|:---:|:---:|
| Self-hostable, no account | ✅ | varies |
| Single command, zero config | ✅ | ⚠️ |
| JSON + SARIF for CI | ✅ | varies |
| MCP-native (AI agents) | ✅ | ❌ |
| Polyglot ports (JS/Go/Rust) | ✅ | ❌ |
| Open license | ✅ COCL | varies |

*Built in the spirit of **EigenPhi / mev-inspect-py**, re-framed the Cognis way. Missing a credit? Open a PR.*

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="integrations"></a>
## Integrations

Pipes into your stack: **SARIF** for code-scanning, **JSON** for anything, an **MCP server** (`mevscope mcp`) for AI agents, and a webhook forwarder for SIEM/Slack/Jira. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="install-anywhere"></a>
## Install — every way, every platform

```bash
pip install "git+https://github.com/cognis-digital/mevscope.git"    # pip (works today)
pipx install "git+https://github.com/cognis-digital/mevscope.git"   # isolated CLI
uv tool install "git+https://github.com/cognis-digital/mevscope.git" # uv
pip install cognis-mevscope                                          # PyPI (when published)
docker run --rm ghcr.io/cognis-digital/mevscope:latest --help        # Docker
brew install cognis-digital/tap/mevscope                             # Homebrew tap
curl -fsSL https://raw.githubusercontent.com/cognis-digital/mevscope/main/install.sh | sh
```

| Linux | macOS | Windows | Docker | Cloud |
|---|---|---|---|---|
| `scripts/setup-linux.sh` | `scripts/setup-macos.sh` | `scripts/setup-windows.ps1` | `docker run ghcr.io/cognis-digital/mevscope` | [DEPLOY.md](docs/DEPLOY.md) (AWS/Azure/GCP/k8s) |

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="related"></a>
## Related Cognis tools

- [`reentryx`](https://github.com/cognis-digital/reentryx) — Static + symbolic detector that flags reentrancy, cross-function, and read-only reentrancy paths in Solidity/Vyper with CI-gating SARIF output.
- [`forkfuzz`](https://github.com/cognis-digital/forkfuzz) — Mainnet-fork invariant fuzzer that replays your contract against live state and stateful sequences to break protocol invariants before deploy.
- [`approvewarden`](https://github.com/cognis-digital/approvewarden) — Scans any wallet for dangerous ERC-20/721/1155 token approvals and infinite allowances, scoring drainer exposure and emitting revoke transactions.
- [`rugradar`](https://github.com/cognis-digital/rugradar) — Token contract risk scanner detecting honeypots, hidden mint/blacklist functions, owner backdoors, and unlocked liquidity before you ape.
- [`storagelens`](https://github.com/cognis-digital/storagelens) — Diffs and decodes contract storage layouts across proxy upgrades to catch storage-collision and uninitialized-slot bugs.
- [`sigsleuth`](https://github.com/cognis-digital/sigsleuth) — Decodes raw calldata and EIP-712 typed-data into human-readable intent, flagging blind-signing and malicious permit/Permit2 payloads.

**Explore the suite →** [🗂️ all 170+ tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources) · [🤖 uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet) · [🧠 engram](https://github.com/cognis-digital/engram)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="contributing"></a>
## Contributing

PRs, new rules, and demo scenarios are welcome under the collaboration-pull model — see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

> ### ⭐ If `mevscope` saved you time, **star it** — it genuinely helps others find it.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

---

<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · one of 170+ tools in the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
