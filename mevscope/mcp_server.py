"""MEVSCOPE MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations

import json
import sys

from mevscope.core import load_swaps_from_obj, build_report


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-mevscope[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-mevscope[mcp]'", file=sys.stderr)
        return 1
    app = FastMCP("mevscope")

    @app.tool()
    def mevscope_scan(swaps_json: str) -> str:
        """Replay a swap-history JSON array and detect sandwich/frontrun MEV.

        Args:
            swaps_json: JSON string — array of swap records or {"swaps": [...]}.

        Returns:
            JSON string with sandwich findings and victim loss accounting.
        """
        try:
            obj = json.loads(swaps_json)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"invalid JSON: {exc}"})
        try:
            swaps = load_swaps_from_obj(obj)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})
        report = build_report(swaps)
        return json.dumps(report.to_dict())

    app.run()
    return 0
