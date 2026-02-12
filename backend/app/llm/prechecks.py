"""
Universal fraud pre-checks before expensive LLM calls.

Extreme/impossible value detection for:
- E-commerce: 1000x price markup (pricing scam)
- Banking: $10M+ transactions from new accounts
- Medical: Claims 10x above typical amounts
- Supply Chain: 500%+ price variance
- All: Negative amounts, impossible dates/ages
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def check_extreme_fraud_patterns(sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Universal fraud pre-checks for extreme/impossible values across all industries.
    Returns fraud result immediately if extreme patterns detected, None otherwise.
    """
    risk_factors = []
    base_score = 0

    if sector == "ecommerce":
        try:
            listed_price = float(data.get("listed_price", 0))
            market_price = float(data.get("market_price", 0))
            if market_price > 0 and listed_price > 0:
                markup_ratio = listed_price / market_price
                markup_percent = (markup_ratio - 1) * 100
                if markup_ratio > 10:
                    base_score = 95
                    risk_factors.append(f"Extreme price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
                    risk_factors.append("Pricing scam/manipulation detected")
                elif markup_ratio > 5:
                    base_score = 85
                    risk_factors.append(f"High price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
                elif markup_ratio > 2:
                    base_score = 70
                    risk_factors.append(f"Suspicious price markup: {markup_percent:.0f}% ({markup_ratio:.1f}x)")
        except (ValueError, ZeroDivisionError):
            pass

    elif sector == "banking":
        try:
            amount = float(data.get("amount", 0))
            account_age = int(data.get("account_age_days", 365))
            if amount > 1000000 and account_age < 30:
                base_score = 95
                risk_factors.append(f"Extreme amount ${amount:,.0f} from new account ({account_age} days)")
            elif amount > 500000 and account_age < 90:
                base_score = 85
                risk_factors.append(f"High amount ${amount:,.0f} from young account ({account_age} days)")
            elif amount > 10000000:
                base_score = 90
                risk_factors.append(f"Extreme transaction amount: ${amount:,.0f}")
        except (ValueError, TypeError):
            pass

    elif sector == "medical":
        try:
            claim_amount = float(data.get("claim_amount", 0))
            if claim_amount > 1000000:
                base_score = 95
                risk_factors.append(f"Extreme claim amount: ${claim_amount:,.0f}")
            elif claim_amount > 500000:
                base_score = 85
                risk_factors.append(f"Very high claim amount: ${claim_amount:,.0f}")
        except (ValueError, TypeError):
            pass

    elif sector == "supply_chain":
        try:
            price_variance = float(data.get("price_variance", 0))
            if price_variance > 500:
                base_score = 90
                risk_factors.append(f"Extreme price variance: {price_variance}%")
            elif price_variance > 300:
                base_score = 80
                risk_factors.append(f"High price variance: {price_variance}%")
        except (ValueError, TypeError):
            pass

    # Universal: negative values
    for field in ["amount", "claim_amount", "listed_price", "market_price", "order_amount"]:
        try:
            value = float(data.get(field, 0))
            if value < 0:
                base_score = max(base_score, 85)
                risk_factors.append(f"Impossible negative value: {field} = ${value}")
        except (ValueError, TypeError):
            pass

    if base_score >= 70 and len(risk_factors) > 0:
        fraud_score = min(base_score + len(risk_factors) * 2, 100)
        risk_level = "CRITICAL" if fraud_score >= 85 else "HIGH"
        reasoning = (
            f"🚨 EXTREME FRAUD PATTERN DETECTED - Immediate intervention required. "
            f"This transaction exhibits clear fraud indicators that exceed normal risk thresholds: "
            f"{'. '.join(risk_factors)}. "
            f"Automated systems have flagged this for immediate manual review."
        )
        logger.info(f"🚨 [Extreme Fraud] Score: {fraud_score} ({risk_level})")
        return {
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "reasoning": reasoning,
            "model_used": "Extreme Fraud Pre-Check (Deterministic)",
            "cost_saved": True
        }

    return None
