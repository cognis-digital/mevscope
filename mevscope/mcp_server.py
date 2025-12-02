"""MEVSCOPE MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from mevscope.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-mevscope[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-mevscope[mcp]'")
        return 1
    app = FastMCP("mevscope")

    @app.tool()
    def mevscope_scan(target: str) -> str:
        """Replays a tx or address history to attribute sandwich, frontrun, and backrun MEV extraction with per-trade loss accounting.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
