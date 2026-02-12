"""
Rule-based explanation builders for fraud analysis (fallback when LLM is unavailable).
"""
from typing import Dict, Any


def explain_banking(data: Dict[str, Any], score: float) -> str:
    factors = []
    amount = data.get("amount", 0)
    if amount > 10000:
        factors.append(f"unusually high transaction amount (${amount:,.2f})")
    location = data.get("location", "")
    if location:
        factors.append(f"transaction from {location}")
    device = data.get("device", "")
    if "new" in str(device).lower():
        factors.append("new or unrecognized device")
    time = data.get("time", "")
    if time:
        factors.append(f"transaction at {time}")
    user_age = data.get("user_age_days", 365)
    if user_age < 30:
        factors.append(f"account age only {user_age} days")

    if factors:
        base = "Red flags detected: " + ", ".join(factors) + "."
        context = " These indicators suggest potential fraudulent activity requiring further investigation."
        return base + context

    return (
        "Transaction appears legitimate with standard patterns. This analysis evaluated transaction amount, "
        "account age, geographic location, device fingerprint, transaction timing, and KYC verification status."
    )


def explain_medical(data: Dict[str, Any], score: float) -> str:
    factors = []
    claim_amount = data.get("claim_amount", 0)
    if claim_amount > 20000:
        factors.append(f"high claim amount (${claim_amount:,.2f})")
    procedures = data.get("procedures", [])
    if isinstance(procedures, list) and len(procedures) > 5:
        factors.append(f"{len(procedures)} procedures in single claim")
    if data.get("diagnosis_mismatch"):
        factors.append("diagnosis-procedure mismatch detected")
    provider = data.get("provider_history", "")
    if "flagged" in str(provider).lower():
        factors.append("provider has previous fraud flags")

    if factors:
        base = "Suspicious indicators: " + ", ".join(factors) + "."
        context = " These indicators suggest potential billing fraud, upcoding, or unnecessary procedures."
        return base + context

    return (
        "Claim follows standard medical billing patterns. This analysis evaluated claim amount, procedure count, "
        "provider history, diagnosis-procedure compatibility, and billing frequency."
    )


def explain_ecommerce(data: Dict[str, Any], score: float) -> str:
    factors = []
    details = []

    seller_age = data.get("seller_age_days", 365)
    if seller_age < 30:
        factors.append(f"seller account only {seller_age} days old")
        details.append("New seller accounts are statistically more likely to engage in fraudulent activities.")

    price = data.get("price", 0)
    market_price = data.get("market_price", price)
    if market_price > 0:
        price_diff = ((price - market_price) / market_price) * 100
        if price < market_price * 0.5:
            discount = abs(price_diff)
            factors.append(f"price {discount:.0f}% below market value")
            details.append("Significant price deviation may indicate counterfeit goods or bait-and-switch schemes.")
        elif price > market_price * 1.5:
            markup = price_diff
            factors.append(f"price {markup:.0f}% above market value")
            details.append("Unusually high pricing suggests potential price gouging.")

    reviews = data.get("reviews", [])
    if isinstance(reviews, list):
        if len(reviews) == 0:
            factors.append("no customer reviews")
            details.append("Lack of customer reviews prevents verification of seller reliability.")
        else:
            negative_keywords = ["negative", "bad", "poor", "terrible", "scam", "fake", "fraud"]
            negative_count = sum(
                1 for r in reviews if any(kw in str(r).lower() for kw in negative_keywords)
            )
            if negative_count > 0:
                factors.append(f"{negative_count} negative review(s)")
                details.append("Negative feedback indicates potential quality issues or fraudulent behavior.")

    shipping = data.get("shipping_location", "")
    if "unknown" in str(shipping).lower() or not shipping:
        factors.append("unclear shipping origin")
        details.append("Unclear shipping origin raises concerns about product authenticity.")

    if factors:
        base = "Warning signs present: " + ", ".join(factors) + "."
        if details:
            base += " " + " ".join(details)
        return base

    return (
        "Listing appears legitimate with typical marketplace patterns. This analysis evaluated seller account "
        "history, pricing consistency, customer feedback, and shipping transparency."
    )


def explain_supply_chain(data: Dict[str, Any], score: float) -> str:
    factors = []
    supplier_age = data.get("supplier_age_days", 365)
    if supplier_age < 30:
        factors.append(f"new supplier ({supplier_age} days)")
    if data.get("payment_terms") == "ADVANCE":
        factors.append("advance payment required")
    price_variance = abs(data.get("price_variance", 0))
    if price_variance > 20:
        factors.append(f"price variance {price_variance:.1f}% from market")
    quality_issues = data.get("quality_issues", 0)
    if quality_issues > 0:
        factors.append(f"{quality_issues} quality issues")
    if not data.get("documentation_complete", True):
        factors.append("incomplete documentation")
    if not data.get("regulatory_compliance", True):
        factors.append("regulatory compliance issues")
    delivery_variance = data.get("delivery_variance", 0)
    if delivery_variance > 20:
        factors.append(f"delivery variance {delivery_variance:.1f}%")

    if factors:
        return "Risk indicators found: " + ", ".join(factors) + "."
    return "Supplier and order profile appear legitimate."


def build_rule_based_explanation(
    sector: str, data: Dict[str, Any], fraud_score: float, risk_level: str, model: str
) -> str:
    """Generate rule-based explanation for a sector."""
    explainers = {
        "banking": explain_banking,
        "medical": explain_medical,
        "ecommerce": explain_ecommerce,
        "supply_chain": explain_supply_chain,
    }
    explain_fn = explainers.get(sector, lambda d, s: "Analysis complete.")
    base = explain_fn(data, fraud_score)
    return f"{model} analysis identifies {risk_level} risk. " + base
