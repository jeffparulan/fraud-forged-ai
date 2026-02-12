"""E-commerce fraud detection prompts."""
from typing import Dict, Any, Optional

from .base_prompts import build_rag_section
from app.llm.ofac import build_ofac_risk_warning


def build_ecommerce_prompt(data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build fraud detection prompt for e-commerce sector."""
    rag_section = build_rag_section(rag_context)

    price = float(data.get('price', data.get('amount', 0)) or 0)
    amount = float(data.get('amount', data.get('price', 0)) or 0)
    market_price = float(data.get('market_price', 0) or 0)
    price_discrepancy = ""
    if market_price > 0 and price > 0:
        discount_pct = ((market_price - price) / market_price) * 100
        if discount_pct > 50:
            price_discrepancy = f"⚠️ CRITICAL: Listed price is {discount_pct:.1f}% below market price (${price} vs ${market_price}) - MAJOR RED FLAG!"
        elif discount_pct > 30:
            price_discrepancy = f"⚠️ WARNING: Listed price is {discount_pct:.1f}% below market price (${price} vs ${market_price})"
    if price > 0 and amount > 0 and price != amount:
        price_diff_pct = abs((price - amount) / max(price, amount)) * 100
        if price_diff_pct > 50:
            price_discrepancy += f"\n⚠️ CRITICAL: Listed price (${price}) differs significantly from order amount (${amount}) - This is suspicious!"

    ofac_warning = build_ofac_risk_warning(data, ['shipping_location', 'shipping_address', 'billing_address', 'origin_country'])

    ip_address = str(data.get('ip_address', '')).lower()
    vpn_risk = "⚠️ WARNING: VPN/Proxy/TOR detected - This is a HIGH-RISK indicator for fraud!" if ('vpn' in ip_address or 'proxy' in ip_address or 'tor' in ip_address) else ""

    email_risk = "⚠️ WARNING: Email NOT verified - Unverified accounts are HIGH-RISK for fraud!" if not data.get('email_verified', False) else ""

    reviews = str(data.get('reviews', ''))
    review_risk = ""
    if any(kw in reviews.lower() for kw in ['scam', 'fraud', 'illegal', 'fake', 'counterfeit', 'do not buy', 'sanction', 'warning']):
        review_risk = "⚠️ CRITICAL: Reviews contain fraud warnings (scam, illegal, fake, etc.) - This is a MAJOR RED FLAG!"

    return f"""You are a senior e-commerce fraud prevention specialist with expertise in online marketplace scams. Analyze this transaction and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{price_discrepancy}
{vpn_risk}
{email_risk}
{review_risk}

Transaction Details:
- Order ID: {data.get('order_id')}
- Seller Age: {data.get('seller_age_days', 'N/A')} days (NEW sellers < 90 days are HIGH RISK)
- Listed Price: ${data.get('price', data.get('amount', 'N/A'))}
- Market Price: ${data.get('market_price', 'N/A')}
- Order Amount: ${data.get('amount', data.get('price', 'N/A'))}
- Shipping Address: {data.get('shipping_address', 'N/A')}
- Billing Address: {data.get('billing_address', 'N/A')}
- Payment Method: {data.get('payment_method', 'N/A')}
- IP Address: {data.get('ip_address', 'N/A')}
- Email Verified: {data.get('email_verified', False)} (FALSE = HIGH RISK)
- Reviews: {data.get('reviews', 'N/A')}
- Shipping Location: {data.get('shipping_location', 'N/A')}
- Product Details: {data.get('product_details', 'N/A')}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious transactions):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Price >50% below market: Add 40-50 points
- VPN/Proxy/TOR detected: Add 25-30 points
- Unverified email: Add 15-20 points
- Negative reviews (scam, fraud, illegal): Add 30-40 points
- New seller (< 30 days): Add 20-30 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present, the score MUST be 70+ (HIGH) or 85+ (CRITICAL).

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., high-risk country, price discrepancy, VPN, unverified email, negative reviews)
4. REASONING: Write 3-4 complete sentences explaining WHY this order is suspicious, WHAT fraud patterns are present, HOW likely this is fraudulent.
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags. Be thorough and specific.]
"""
