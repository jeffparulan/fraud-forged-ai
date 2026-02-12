"""
DEPRECATED: Use app.mcp.client instead.

Re-export for backward compatibility.
"""
from app.mcp.client import MCPClient, get_mcp_client

__all__ = ["MCPClient", "get_mcp_client"]
