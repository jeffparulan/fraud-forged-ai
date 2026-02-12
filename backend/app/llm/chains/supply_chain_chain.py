"""Supply chain fraud scoring chain."""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def score_supply_chain_fraud(data: Dict[str, Any]) -> float:
    """Supply chain fraud scoring - supplier age, price variance, documentation, kickbacks."""
    score = 0.0

    payment_terms = str(data.get("payment_terms", "")).upper()
    if payment_terms == "ADVANCE":
        score += 40
    elif payment_terms == "COD":
        score += 10

    try:
        supplier_age = int(data.get("supplier_age_days", 365))
    except (ValueError, TypeError):
        supplier_age = 365
    if supplier_age < 1:
        score += 50
    elif supplier_age < 7:
        score += 45
    elif supplier_age < 30:
        score += 30
    elif supplier_age < 90:
        score += 15
    elif supplier_age >= 1095:
        score -= 10
    elif supplier_age >= 730:
        score -= 5

    price_variance = abs(float(data.get("price_variance", 0)))
    order_details = str(data.get("order_details", "")).lower()
    has_kickback = any(f in order_details for f in ["kickback", "personal relationship", "bribery", "above market"])

    if price_variance > 40:
        score += 40 if has_kickback else 35
    elif price_variance > 30:
        score += 35 if has_kickback else 30
    elif price_variance > 20:
        score += 20
    elif price_variance > 10:
        score += 10
    elif price_variance < 5:
        score -= 5

    quality_issues = int(data.get("quality_issues", 0))
    if quality_issues > 5:
        score += 35
    elif quality_issues > 2:
        score += 30 if has_kickback else 25
    elif quality_issues > 0:
        score += 20 if has_kickback else 10

    if not data.get("documentation_complete", True):
        score += 30
    if not data.get("regulatory_compliance", True):
        score += 35
    if data.get("documentation_complete", True) and data.get("regulatory_compliance", True):
        score -= 5

    delivery_variance = abs(float(data.get("delivery_variance", 0)))
    if delivery_variance > 80:
        score += 25
    elif delivery_variance > 50:
        score += 20
    elif delivery_variance > 20:
        score += 10
    elif delivery_variance < 5:
        score -= 5

    try:
        order_amount = float(data.get("order_amount", 0))
    except (ValueError, TypeError):
        order_amount = 0.0
    if order_amount > 100000 and supplier_age < 30:
        score += 20
    elif order_amount > 200000:
        score += 10

    critical_flags = ["kickback", "bribery", "corruption", "personal relationship", "conflict of interest", "under the table"]
    if any(flag in order_details for flag in critical_flags):
        score += 40

    high_risk_flags = ["ghost", "unverified", "no references", "no online presence", "suspicious", "fraud", "inferior quality", "overpriced"]
    if any(flag in order_details for flag in high_risk_flags):
        score += 25

    medium_risk_flags = ["unusual", "irregular", "questionable", "concerning"]
    if any(flag in order_details for flag in medium_risk_flags):
        score += 15

    legitimate_keywords = ["established", "regular", "verified", "5-year", "history", "legitimate", "competitive pricing"]
    if any(kw in order_details for kw in legitimate_keywords) and score < 30:
        score -= 10

    return max(0, min(100, score))
