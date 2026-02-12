"""E-commerce fraud scoring chain."""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

NEGATIVE_KEYWORDS = [
    "bad", "scam", "fraud", "fake", "counterfeit", "poor", "terrible",
    "worst", "awful", "never received", "stolen", "illegal", "suspicious",
    "delays", "never arrived", "defective", "broken", "misleading",
]


def score_ecommerce_fraud(data: Dict[str, Any]) -> float:
    """E-commerce fraud scoring - seller age, pricing, reviews, verification."""
    score = 0.0

    try:
        seller_age = int(data.get("seller_age_days", 365))
    except (ValueError, TypeError):
        seller_age = 365
    if seller_age < 1:
        score += 45
    elif seller_age < 7:
        score += 40
    elif seller_age < 30:
        score += 25
    elif seller_age < 90:
        score += 10
    elif seller_age >= 730:
        score -= 10

    price = float(data.get("listed_price", 0)) or float(data.get("price", 0))
    market_price = float(data.get("market_price", price))
    if market_price > 0 and price > 0:
        markup_ratio = price / market_price
        if markup_ratio > 10:
            score += 60
        elif markup_ratio > 5:
            score += 45
        elif markup_ratio > 2:
            score += 30
        elif price < market_price:
            discount_pct = ((market_price - price) / market_price) * 100
            if discount_pct > 70:
                score += 50
            elif discount_pct > 50:
                score += 40
            elif discount_pct > 30:
                score += 25
        elif 0.9 <= markup_ratio <= 1.1:
            score -= 5

    order_amount = float(data.get("amount", 0)) or float(data.get("order_amount", 0))
    if price > 0 and order_amount > price:
        order_markup_ratio = order_amount / price
        if order_markup_ratio >= 10.0:
            score += 60
        elif order_markup_ratio >= 5.0:
            score += 45
        elif order_markup_ratio >= 2.0:
            score += 30

    shipping_address = str(data.get("shipping_address", "")).lower()
    billing_address = str(data.get("billing_address", "")).lower()
    if shipping_address and billing_address and shipping_address.replace(" ", "") != billing_address.replace(" ", ""):
        score += 30
    elif shipping_address and billing_address and shipping_address == billing_address:
        score -= 5

    payment_method = str(data.get("payment_method", "")).lower()
    if any(m in payment_method for m in ["crypto", "gift_card", "prepaid", "other"]):
        score += 20
    elif payment_method in ["credit_card", "debit_card"]:
        score -= 5

    ip_address = str(data.get("ip_address", "")).lower()
    if "vpn" in ip_address or "tor" in ip_address or "proxy" in ip_address:
        score += 25
    elif "unknown" in ip_address or ip_address == "":
        score += 10

    if not data.get("email_verified", False):
        score += 15
    else:
        score -= 5

    reviews = data.get("reviews", [])
    if isinstance(reviews, list):
        if len(reviews) == 0:
            score += 20
        elif len(reviews) < 5:
            score += 10
        negative_count = sum(1 for r in reviews if any(kw in str(r).lower() for kw in NEGATIVE_KEYWORDS))
        if negative_count > 0:
            score += min(40, negative_count * 15)
        elif len(reviews) > 0 and all("excellent" in str(r).lower() or "5" in str(r) for r in reviews[:5]):
            score += 30
    elif isinstance(reviews, str):
        if not reviews or reviews.lower() == "none":
            score += 20
        else:
            negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in reviews.lower())
            if negative_count > 0:
                score += min(40, negative_count * 10)

    if not data.get("seller_verified", False) and seller_age < 30:
        score += 15

    shipping = str(data.get("shipping_location", "")).lower()
    if "unknown" in shipping or shipping == "":
        score += 25
    elif shipping in ["united states", "canada", "united kingdom", "germany", "france"]:
        score -= 5

    product_details = str(data.get("product_details", "")).lower()
    description = str(data.get("description", product_details)).lower()
    if "stock photo" in description or "vague" in description or len(description) < 20:
        score += 15
    elif "authentic" in description or "verified" in description:
        score -= 5

    return max(0, min(100, score))
