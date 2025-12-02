"""
Model Context Protocol (MCP) Client Integration

MCP allows AI models to access external tools, data sources, and services
in a standardized way. This enables:
- Dynamic tool discovery
- Structured data access
- Enhanced context for fraud detection
- Integration with external APIs and databases
"""

import logging
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Model Context Protocol client for enhanced fraud detection.
    
    MCP enables models to:
    - Access external data sources (blockchain, payment processors, etc.)
    - Use specialized tools (address validation, transaction history)
    - Get real-time context (market data, risk scores)
    """
    
    def __init__(self, mcp_server_url: Optional[str] = None):
        """
        Initialize MCP client.
        
        Args:
            mcp_server_url: Optional MCP server URL. If not provided,
                          uses environment variable MCP_SERVER_URL
        """
        import os
        self.mcp_server_url = mcp_server_url or os.getenv("MCP_SERVER_URL")
        if not self.mcp_server_url:
            logger.warning("No MCP server URL configured - MCP features disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ MCP Client initialized: {self.mcp_server_url}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Discover available MCP tools.
        
        Returns:
            List of available tools with their schemas
        """
        if not self.enabled:
            return []
        
        try:
            response = httpx.post(
                f"{self.mcp_server_url}/tools/list",
                timeout=5.0
            )
            response.raise_for_status()
            return response.json().get("tools", [])
        except Exception as e:
            logger.warning(f"Could not fetch MCP tools: {e}")
            return []
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        
        Returns:
            Tool result
        """
        if not self.enabled:
            return {"error": "MCP not enabled"}
        
        try:
            response = httpx.post(
                f"{self.mcp_server_url}/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return {"error": str(e)}
    
    def get_context(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get enhanced context for fraud detection using MCP tools.
        
        Args:
            sector: Fraud detection sector (banking, medical, etc.)
            data: Transaction/claim data
        
        Returns:
            Enhanced context with external data
        """
        if not self.enabled:
            return {}
        
        context = {}
        
        # Sector-specific MCP tool calls
        if sector == "banking":
            # Check blockchain addresses if crypto transaction
            if "sender_wallet" in data or "receiver_wallet" in data:
                context["blockchain_data"] = self._check_blockchain(
                    data.get("sender_wallet"),
                    data.get("receiver_wallet")
                )
            
            # Check transaction history
            if "transaction_id" in data:
                context["transaction_history"] = self._get_transaction_history(
                    data["transaction_id"]
                )
        
        elif sector == "medical":
            # Check provider credentials
            if "provider_id" in data:
                context["provider_data"] = self._check_provider(
                    data["provider_id"]
                )
        
        elif sector == "ecommerce":
            # Check seller reputation
            if "seller_id" in data:
                context["seller_data"] = self._check_seller(
                    data.get("seller_id")
                )
        
        return context
    
    def _check_blockchain(self, sender: Optional[str], receiver: Optional[str]) -> Dict[str, Any]:
        """Check blockchain addresses using MCP tools."""
        result = {}
        if sender:
            result["sender"] = self.call_tool("check_wallet_address", {"address": sender})
        if receiver:
            result["receiver"] = self.call_tool("check_wallet_address", {"address": receiver})
        return result
    
    def _get_transaction_history(self, tx_id: str) -> Dict[str, Any]:
        """Get transaction history using MCP tools."""
        return self.call_tool("get_transaction_history", {"transaction_id": tx_id})
    
    def _check_provider(self, provider_id: str) -> Dict[str, Any]:
        """Check healthcare provider credentials using MCP tools."""
        return self.call_tool("check_provider_credentials", {"provider_id": provider_id})
    
    def _check_seller(self, seller_id: Optional[str]) -> Dict[str, Any]:
        """Check e-commerce seller reputation using MCP tools."""
        if not seller_id:
            return {}
        return self.call_tool("check_seller_reputation", {"seller_id": seller_id})


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

