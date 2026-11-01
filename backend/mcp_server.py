from __future__ import annotations

import os
from typing import Any

from agent_runtime import AuthorizationContext, mcp_connector_gateway, trust_engine

MCP_SERVER = None
MCP_APP = None
MCP_AVAILABLE = False
MCP_IMPORT_ERROR = None

try:
    from mcp.server import MCPServer
    from mcp.server.transport_security import TransportSecuritySettings

    MCP_SERVER = MCPServer("zhiyintong-mock-bank-connector")

    @MCP_SERVER.tool()
    async def account_get_overview() -> dict[str, Any]:
        """Read the synthetic demo account overview. Read-only GREEN operation."""
        decision = trust_engine.authorize("account.read", AuthorizationContext())
        if decision.decision != "ALLOW":
            return {"decision": decision.model_dump(), "data": None}
        return {"decision": decision.model_dump(), "data": mcp_connector_gateway.call_read_tool("account.get_overview"), "simulated_only": True}

    @MCP_SERVER.tool()
    async def bills_get_spending_summary() -> dict[str, Any]:
        """Read categorized synthetic spending data. Read-only GREEN operation."""
        decision = trust_engine.authorize("bills.read", AuthorizationContext())
        if decision.decision != "ALLOW":
            return {"decision": decision.model_dump(), "data": None}
        return {"decision": decision.model_dump(), "items": mcp_connector_gateway.call_read_tool("bills.get_spending_summary"), "simulated_only": True}

    @MCP_SERVER.tool()
    async def cards_get_status() -> dict[str, Any]:
        """Read a masked synthetic card status. Read-only GREEN operation."""
        decision = trust_engine.authorize("cards.read", AuthorizationContext())
        if decision.decision != "ALLOW":
            return {"decision": decision.model_dump(), "data": None}
        return {"decision": decision.model_dump(), "data": mcp_connector_gateway.call_read_tool("cards.get_status"), "simulated_only": True}

    @MCP_SERVER.tool()
    async def transfer_preview(amount: float, recipient_is_known: bool = False) -> dict[str, Any]:
        """Preview a transfer risk decision. This tool never executes a transfer."""
        decision = trust_engine.authorize("transfer.preview", AuthorizationContext())
        flags = [] if recipient_is_known else ["new_recipient"]
        if amount >= 5000:
            flags.append("large_amount")
        return {
            "preview_decision": decision.model_dump(),
            "risk_flags": flags,
            "execution": "NOT_EXECUTED",
            "simulated_only": True,
        }

    @MCP_SERVER.tool()
    async def wealth_list_products() -> dict[str, Any]:
        """List synthetic demo wealth products. Read-only GREEN operation; not investment advice."""
        decision = trust_engine.authorize("wealth.read", AuthorizationContext())
        products = mcp_connector_gateway.call_read_tool("wealth.list_products") if decision.decision == "ALLOW" else []
        return {"decision": decision.model_dump(), "products": products, "simulated_only": True}

    @MCP_SERVER.tool()
    async def subscription_cancel_request(subscription_id: str) -> dict[str, Any]:
        """Create a cancellation approval request. The model cannot assert human consent; no merchant is contacted."""
        decision = trust_engine.authorize(
            "subscription.cancel", AuthorizationContext(), user_confirmed=False,
            mfa_verified=False, simulation_only=True,
        )
        return {"subscription_id": subscription_id, "decision": decision.model_dump(), "merchant_contacted": False, "simulated_only": True}

    @MCP_SERVER.tool()
    async def wealth_subscription_request() -> dict[str, Any]:
        """Create a wealth-subscription approval request. The model cannot assert human consent or MFA; no order is placed."""
        decision = trust_engine.authorize(
            "wealth.subscribe", AuthorizationContext(), user_confirmed=False,
            mfa_verified=False, simulation_only=True,
        )
        return {"decision": decision.model_dump(), "order_submitted": False, "simulated_only": True}

    @MCP_SERVER.tool()
    async def card_freeze_request() -> dict[str, Any]:
        """Create a simulated card-freeze approval request. The model cannot assert human consent or MFA; no real card is changed."""
        decision = trust_engine.authorize(
            "card.freeze", AuthorizationContext(), user_confirmed=False,
            mfa_verified=False, simulation_only=True,
        )
        return {"decision": decision.model_dump(), "card_status_changed": False, "simulated_only": True}

    @MCP_SERVER.tool()
    async def transfer_execute(
        amount: float,
        recipient_is_known: bool = False,
    ) -> dict[str, Any]:
        """Create a transfer approval check. The model cannot assert human consent or MFA; the mock connector never moves funds."""
        flags = [] if recipient_is_known else ["new_recipient"]
        if amount >= 5000:
            flags.append("large_amount")
        decision = trust_engine.authorize(
            "transfer.execute", AuthorizationContext(), user_confirmed=False,
            mfa_verified=False, risk_flags=flags, simulation_only=True,
        )
        return {"decision": decision.model_dump(), "execution": "BLOCKED_OR_SIMULATED_ONLY", "funds_moved": False}

    allowed_hosts = [x.strip() for x in os.getenv("MCP_ALLOWED_HOSTS", "localhost:8000,127.0.0.1:8000").split(",") if x.strip()]
    allowed_origins = [x.strip() for x in os.getenv("MCP_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001").split(",") if x.strip()]
    transport_security = TransportSecuritySettings(
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    MCP_APP = MCP_SERVER.streamable_http_app(
        streamable_http_path="/",
        transport_security=transport_security,
    )
    MCP_AVAILABLE = True
except Exception as exc:  # Optional dependency: the FastAPI app remains available without MCP.
    MCP_IMPORT_ERROR = type(exc).__name__
    MCP_SERVER = None
    MCP_APP = None
    MCP_AVAILABLE = False
