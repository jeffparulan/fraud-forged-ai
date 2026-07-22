"""Banking/crypto fraud scoring chain.

Each signal contributes explicit points. The final score is clamped to 0–100,
but we also return a breakdown so the UI can show why flipping KYC (or TOR,
country, velocity, etc.) moved — or did not move — the visible score when
many critical signals already saturate the ceiling.
"""
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# Offshore / high-risk jurisdictions commonly used in laundering demos
HIGH_RISK_LOCATIONS = [
    "nigeria", "russia", "china", "unknown",
    "cayman islands", "british virgin islands", "bvi",
    "panama", "seychelles", "mauritius", "cyprus",
]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


def score_banking_fraud_detailed(data: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Return (clamped_score, breakdown).

    Each breakdown item: {label, points, signal} where points may be +/−.
    """
    breakdown: List[Dict[str, Any]] = []
    raw = 0.0

    def add(label: str, points: float, signal: str) -> None:
        nonlocal raw
        raw += points
        breakdown.append({"label": label, "points": points, "signal": signal})

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0
    if amount > 100000:
        add(f"High amount (${amount:,.0f})", 30, "amount")
    elif amount > 50000:
        add(f"Elevated amount (${amount:,.0f})", 20, "amount")
    elif amount > 10000:
        add(f"Material amount (${amount:,.0f})", 15, "amount")
    elif amount > 5000:
        add(f"Moderate amount (${amount:,.0f})", 10, "amount")
    elif 0 < amount < 1000:
        add(f"Small amount (${amount:,.0f})", -10, "amount")

    location = str(data.get("location", "")).lower()
    source_country = str(data.get("source_country", "")).lower()
    dest_country = str(data.get("destination_country", "")).lower()
    if any(
        loc in location or loc in source_country or loc in dest_country
        for loc in HIGH_RISK_LOCATIONS
    ):
        matched = next(
            (
                loc for loc in HIGH_RISK_LOCATIONS
                if loc in location or loc in source_country or loc in dest_country
            ),
            "high-risk jurisdiction",
        )
        add(f"High-risk geography ({matched})", 30, "geography")
    elif "united states" in location or "united states" in source_country:
        add("Domestic US source", -5, "geography")

    ip_address = str(data.get("ip_address", "")).lower()
    if "tor" in ip_address or "vpn detected" in ip_address:
        add("TOR/VPN network", 25, "network")
    elif "unknown" in ip_address:
        add("Unknown network", 15, "network")

    transaction_type = str(data.get("transaction_type", "")).lower()
    if "crypto" in transaction_type or "nft" in transaction_type:
        add(f"Crypto/NFT type ({transaction_type or 'crypto'})", 15, "txn_type")

    time_str = str(data.get("time", "") or data.get("transaction_time", "")).lower()
    if time_str and ":" in time_str:
        try:
            hour = int(time_str.split(":")[0])
            if 0 <= hour < 6:
                add(f"Off-hours transaction ({time_str})", 15, "timing")
            elif hour >= 22:
                add(f"Late-night transaction ({time_str})", 10, "timing")
        except (ValueError, TypeError):
            pass

    try:
        account_age = int(data.get("account_age_days", 365))
    except (ValueError, TypeError):
        account_age = 365
    if account_age < 1:
        add("Brand-new account (<1 day)", 30, "account_age")
    elif account_age < 7:
        add(f"Very new account ({account_age} days)", 25, "account_age")
    elif account_age < 30:
        add(f"New account ({account_age} days)", 15, "account_age")
    elif account_age < 90:
        add(f"Young account ({account_age} days)", 5, "account_age")
    elif account_age >= 730:
        add(f"Established account ({account_age} days)", -15, "account_age")
    elif account_age >= 365:
        add(f"Mature account ({account_age} days)", -10, "account_age")

    try:
        velocity = int(data.get("transaction_velocity", 0))
    except (ValueError, TypeError):
        velocity = 0
    if velocity > 20:
        add(f"Extreme velocity ({velocity} txns/24h)", 25, "velocity")
    elif velocity > 10:
        add(f"High velocity ({velocity} txns/24h)", 15, "velocity")
    elif velocity > 5:
        add(f"Elevated velocity ({velocity} txns/24h)", 5, "velocity")
    elif velocity <= 2 and velocity >= 0:
        add(f"Normal velocity ({velocity} txns/24h)", -5, "velocity")

    # KYC: flipping this is a 45-point swing (−20 vs +25)
    if _as_bool(data.get("kyc_verified", False)):
        add("KYC verified", -20, "kyc")
    else:
        add("KYC not verified", 25, "kyc")

    # Form sends previous_flagged; accept both spellings
    if _as_bool(data.get("previous_flagged", data.get("previously_flagged", False))):
        add("Previously flagged", 30, "history")

    sender_wallet = str(data.get("sender_wallet", "")).lower()
    receiver_wallet = str(data.get("receiver_wallet", "")).lower()
    zero_marker = "000000000000000000000000"
    if zero_marker in sender_wallet or zero_marker in receiver_wallet:
        add("Burn/null wallet address detected", 40, "wallet")
    elif "tornado" in sender_wallet or "tornado" in receiver_wallet:
        add("Tornado Cash / mixer-linked wallet", 40, "wallet")

    clamped = max(0.0, min(100.0, raw))
    if raw > 100:
        breakdown.append({
            "label": f"Score saturated (raw {raw:.0f} → clamped 100)",
            "points": 0,
            "signal": "clamp",
        })
    elif raw < 0:
        breakdown.append({
            "label": f"Score floored (raw {raw:.0f} → clamped 0)",
            "points": 0,
            "signal": "clamp",
        })

    return clamped, breakdown


def score_banking_fraud(data: Dict[str, Any]) -> float:
    """Banking/crypto fraud scoring - amount, location, KYC, velocity, account age."""
    score, _ = score_banking_fraud_detailed(data)
    return score
