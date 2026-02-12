"""Banking/crypto fraud scoring chain."""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def score_banking_fraud(data: Dict[str, Any]) -> float:
    """Banking/crypto fraud scoring - amount, location, KYC, velocity, account age."""
    score = 0.0

    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0
    if amount > 100000:
        score += 30
    elif amount > 50000:
        score += 20
    elif amount > 10000:
        score += 15
    elif amount > 5000:
        score += 10
    elif amount < 1000:
        score -= 10

    location = str(data.get("location", "")).lower()
    source_country = str(data.get("source_country", "")).lower()
    dest_country = str(data.get("destination_country", "")).lower()
    high_risk_locations = ["nigeria", "russia", "china", "unknown", "cayman islands"]
    if any(loc in location or loc in source_country or loc in dest_country for loc in high_risk_locations):
        score += 30
    elif "united states" in location or "united states" in source_country:
        score -= 5

    ip_address = str(data.get("ip_address", "")).lower()
    if "tor" in ip_address or "vpn detected" in ip_address:
        score += 25
    elif "unknown" in ip_address:
        score += 15

    transaction_type = str(data.get("transaction_type", "")).lower()
    if "crypto" in transaction_type or "nft" in transaction_type:
        score += 15

    time_str = str(data.get("time", "") or data.get("transaction_time", "")).lower()
    if time_str and ":" in time_str:
        try:
            hour = int(time_str.split(":")[0])
            if 0 <= hour < 6:
                score += 15
            elif hour >= 22:
                score += 10
        except (ValueError, TypeError):
            pass

    try:
        account_age = int(data.get("account_age_days", 365))
    except (ValueError, TypeError):
        account_age = 365
    if account_age < 1:
        score += 30
    elif account_age < 7:
        score += 25
    elif account_age < 30:
        score += 15
    elif account_age < 90:
        score += 5
    elif account_age >= 730:
        score -= 15
    elif account_age >= 365:
        score -= 10

    try:
        velocity = int(data.get("transaction_velocity", 0))
    except (ValueError, TypeError):
        velocity = 0
    if velocity > 20:
        score += 25
    elif velocity > 10:
        score += 15
    elif velocity > 5:
        score += 5
    elif velocity <= 2:
        score -= 5

    if data.get("kyc_verified", False):
        score -= 20
    else:
        score += 25

    if data.get("previous_flagged", False):
        score += 30

    sender_wallet = str(data.get("sender_wallet", "")).lower()
    receiver_wallet = str(data.get("receiver_wallet", "")).lower()
    if sender_wallet and ("0000000000000000000000000000000000000000" in sender_wallet or "tornado" in receiver_wallet):
        score += 40

    return max(0, min(100, score))
