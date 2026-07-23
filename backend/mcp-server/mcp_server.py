"""
MCP Server Implementation for FraudForge AI

Lightweight demo MCP server (Cloud Run / docker-compose free tier).
Returns deterministic tool results so the LangGraph enrich_mcp stage can
show mcp: ok in the decision trace without paid external APIs.
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="FraudForge AI MCP Server")

# Demo wallets that trigger guardrail-visible flags (see BankingForm samples)
NULL_ADDRESS_PREFIX = "0x000"
MIXER_DEMO_WALLETS = {
    "0xd4c7f8e19ab6d6e6f3e2c7b8f9da1c2e3f4a5b6c",  # Crypto Mixer sample sender
}

MCP_TOOLS = [
    {
        "name": "check_wallet_address",
        "description": "Check blockchain wallet address for suspicious activity",
        "inputSchema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Blockchain wallet address"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_transaction_history",
        "description": "Get transaction history for a given transaction ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "description": "Transaction ID to lookup"}
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "check_provider_credentials",
        "description": "Verify healthcare provider credentials and license status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider_id": {"type": "string", "description": "Healthcare provider ID"}
            },
            "required": ["provider_id"],
        },
    },
    {
        "name": "check_seller_reputation",
        "description": "Check e-commerce seller reputation and history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "seller_id": {"type": "string", "description": "Seller ID or username"}
            },
            "required": ["seller_id"],
        },
    },
]


def _tools_payload() -> Dict[str, List[Dict[str, Any]]]:
    return {"tools": MCP_TOOLS}


@app.get("/")
def root():
    return {
        "service": "FraudForge AI MCP Server",
        "status": "operational",
        "protocol": "Model Context Protocol",
        "version": "1.1.0",
        "mode": "demo_deterministic",
    }


@app.get("/health")
def health():
    """Reachability probe used by the FraudForge MCP client."""
    return {"status": "healthy", "service": "fraudforge-mcp", "mode": "demo_deterministic"}


@app.get("/tools/list")
@app.post("/tools/list")
def list_tools():
    """List available MCP tools (GET and POST — client may use either)."""
    return _tools_payload()


@app.post("/tools/call")
def call_tool(request: Dict[str, Any]):
    """
    Call an MCP tool.

    Expected format:
    {
        "name": "tool_name",
        "arguments": {...}
    }
    """
    tool_name = request.get("name")
    arguments = request.get("arguments", {})

    if not tool_name:
        raise HTTPException(status_code=400, detail="Tool name required")

    if tool_name == "check_wallet_address":
        return _check_wallet_address(arguments.get("address"))
    if tool_name == "get_transaction_history":
        return _get_transaction_history(arguments.get("transaction_id"))
    if tool_name == "check_provider_credentials":
        return _check_provider_credentials(arguments.get("provider_id"))
    if tool_name == "check_seller_reputation":
        return _check_seller_reputation(arguments.get("seller_id"))

    raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")


def _check_wallet_address(address: Optional[str]) -> Dict[str, Any]:
    """Deterministic wallet risk signals for the demo pipeline."""
    if not address:
        return {"error": "Address required", "source": "fraudforge_mcp_demo"}

    addr_lower = address.lower()
    is_null = addr_lower.startswith(NULL_ADDRESS_PREFIX)
    is_mixer = addr_lower in MIXER_DEMO_WALLETS

    tags: List[str] = []
    if is_null:
        tags.append("null_address")
    if is_mixer:
        tags.append("mixer")

    return {
        "address": address,
        "risk_score": 0.95 if (is_null or is_mixer) else 0.12,
        "transaction_count": 12 if is_mixer else (2 if is_null else 150),
        "first_seen": "2024-01-15",
        "is_contract": False,
        "high_risk": bool(is_null or is_mixer),
        "mixer": is_mixer,
        "sanctioned": is_null,
        "tags": tags,
        "source": "fraudforge_mcp_demo",
    }


def _get_transaction_history(tx_id: Optional[str]) -> Dict[str, Any]:
    if not tx_id:
        return {"error": "Transaction ID required", "source": "fraudforge_mcp_demo"}

    return {
        "transaction_id": tx_id,
        "history": [
            {"date": "2024-11-15", "amount": 1000, "type": "transfer"},
            {"date": "2024-11-10", "amount": 500, "type": "deposit"},
        ],
        "risk_indicators": [],
        "source": "fraudforge_mcp_demo",
    }


def _check_provider_credentials(provider_id: Optional[str]) -> Dict[str, Any]:
    if not provider_id:
        return {"error": "Provider ID required", "source": "fraudforge_mcp_demo"}

    # Demo: PRV-77432 (and similar flagged samples) look risky
    flagged = provider_id.upper() in {"PRV-77432", "PRV-88990"}
    return {
        "provider_id": provider_id,
        "license_status": "suspended" if flagged else "active",
        "specialty": "Cardiology",
        "years_practicing": 2 if flagged else 15,
        "complaints": 7 if flagged else 0,
        "verified": not flagged,
        "high_risk": flagged,
        "source": "fraudforge_mcp_demo",
    }


def _check_seller_reputation(seller_id: Optional[str]) -> Dict[str, Any]:
    if not seller_id:
        return {"error": "Seller ID required", "source": "fraudforge_mcp_demo"}

    sid = seller_id.upper()
    suspicious = any(token in sid for token in ("SUSP", "NEW", "FAKE", "RISK"))
    return {
        "seller_id": seller_id,
        "rating": 2.1 if suspicious else 4.5,
        "total_reviews": 8 if suspicious else 1250,
        "account_age_days": 3 if suspicious else 365,
        "verified": not suspicious,
        "suspicious_activity": suspicious,
        "high_risk": suspicious,
        "source": "fraudforge_mcp_demo",
    }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
