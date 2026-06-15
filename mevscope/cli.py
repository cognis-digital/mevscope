"""MEVSCOPE command-line interface.

Examples:
    # Scan a swap history file, human-readable table
    python -m mevscope scan demos/01-basic/swaps.json

    # JSON output for piping / CI gates
    python -m mevscope scan swaps.json --format json | jq .total_victim_loss

    # Treat any detected sandwich as a CI failure (non-zero exit)
    python -m mevscope scan swaps.json --fail-on-mev

Exit codes:
    0  no sandwiches detected
    1  sandwiches detected AND --fail-on-mev set (CI gate)
    2  usage / input error
"""
from __future__ import annotations

import argparse
import json
import sys

from . import TOOL_NAME, TOOL_VERSION
from .core import load_swaps, build_report, Report


def _fmt_table(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"MEVSCOPE  swaps analyzed: {report.swaps_analyzed}  "
                 f"sandwiches: {len(report.sandwiches)}")
    if not report.sandwiches:
        lines.append("No sandwich attacks detected.")
        return "\n".join(lines)
    lines.append("")
    header = f"{'BLOCK':>8}  {'VICTIM TX':<14}  {'PAIR':<14}  {'LOSS (in)':>14}  {'ATTACKER PROFIT':>16}  {'METHOD':<9}"
    lines.append(header)
    lines.append("-" * len(header))
    for s in report.sandwiches:
        pair = f"{s.token_in}->{s.token_out}"
        vtx = (s.victim_tx[:12] + "..") if len(s.victim_tx) > 14 else s.victim_tx
        lines.append(
            f"{s.block:>8}  {vtx:<14}  {pair:<14}  "
            f"{s.victim_loss_in:>14.6f}  "
            f"{s.attacker_profit:>12.6f} {s.profit_token:<3}  {s.method:<9}"
        )
    lines.append("-" * len(header))
    lines.append(
        f"TOTAL victim loss: {report.total_victim_loss:.6f}   "
        f"attacker profit: {report.total_attacker_profit:.6f}"
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Replay DEX swap history and attribute sandwich/frontrun MEV "
                    "with per-trade victim loss accounting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python -m mevscope scan demos/01-basic/swaps.json\n"
               "  python -m mevscope scan swaps.json --format json | jq .\n"
               "  python -m mevscope scan swaps.json --fail-on-mev   # CI gate\n",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    scan = sub.add_parser(
        "scan",
        help="scan a swap-history JSON file for sandwich attacks",
        description="Scan a chronological swap-history JSON file and report "
                    "detected sandwich attacks plus victim losses.",
    )
    scan.add_argument("file", help="path to swap-history JSON "
                                   "(array of swaps or {'swaps': [...]})")
    scan.add_argument("--format", choices=["table", "json"], default="table",
                      help="output format (default: table)")
    scan.add_argument("--fail-on-mev", action="store_true",
                      help="exit non-zero if any sandwich is detected (CI gate)")
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "scan":
        parser.print_help()
        return 0

    try:
        swaps = load_swaps(args.file)
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"error: permission denied reading file: {args.file}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as e:
        print(f"error: could not parse swaps: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # noqa: BLE001
        print(f"error: unexpected error loading file: {e}", file=sys.stderr)
        return 2

    try:
        report = build_report(swaps)
    except Exception as e:  # noqa: BLE001
        print(f"error: analysis failed: {e}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(_fmt_table(report))

    if args.fail_on_mev and report.sandwiches:
        return 1
    return 0
