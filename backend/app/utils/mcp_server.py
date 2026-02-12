"""
DEPRECATED: Use app.mcp.servers.fraud_server instead.

Re-export for backward compatibility.
"""
from app.mcp.servers.fraud_server import app, MCP_TOOLS

__all__ = ["app", "MCP_TOOLS"]
