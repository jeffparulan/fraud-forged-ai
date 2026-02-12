"""Banking fraud detection prompts."""
from typing import Dict, Any, Optional

from .base_prompts import build_rag_section
from app.llm.ofac import build_ofac_risk_warning


def build_banking_prompt(data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build fraud detection prompt for banking/crypto sector."""
    rag_section = build_rag_section(rag_context)
    ofac_warning = build_ofac_risk_warning(data, ['source_country', 'destination_country', 'location'])

    ip_address = str(data.get('ip_address', '')).lower()
    vpn_risk = ""
    if 'vpn' in ip_address or 'proxy' in ip_address or 'tor' in ip_address:
        vpn_risk = "⚠️ WARNING: VPN/Proxy/TOR detected - This is a HIGH-RISK indicator for fraud!"

    wallet_info = ""
    if data.get('sender_wallet') or data.get('receiver_wallet'):
        wallet_info = f"""
Blockchain Details (Crypto Transaction):
- Sender Wallet: {data.get('sender_wallet', 'N/A')}
- Receiver Wallet: {data.get('receiver_wallet', 'N/A')}
- Note: Check wallet addresses against known fraud databases and Etherscan for transaction history
"""

    return f"""You are a senior financial fraud analyst with 15 years of experience. Analyze this transaction and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{vpn_risk}

Transaction Details:
- Transaction ID: {data.get('transaction_id')}
- Type: {data.get('transaction_type')}
- Amount: ${data.get('amount')}
- Source Country: {data.get('source_country')}
- Destination Country: {data.get('destination_country')}
- Account Age: {data.get('account_age_days')} days (NEW accounts < 90 days are HIGH RISK)
- KYC Verified: {data.get('kyc_verified')} (FALSE = HIGH RISK)
- Previously Flagged: {data.get('previously_flagged')}
- Transaction Velocity: {data.get('transaction_velocity', 'N/A')} transactions in 24h
- IP Address: {data.get('ip_address', 'N/A')}
{wallet_info}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious transactions):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- VPN/Proxy/TOR detected: Add 25-30 points
- Unverified KYC: Add 15-20 points
- New account (< 30 days): Add 20-30 points
- High transaction velocity (> 10/day): Add 15-20 points
- Large amounts (> $10,000): Add 15-25 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., OFAC country + VPN + unverified + new account), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, VPN, unverified KYC, new account, high velocity)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this transaction is flagged (cite ALL red flags: country, VPN, KYC, account age, velocity, amount)
   - WHAT patterns indicate fraud (be specific about the ${data.get('amount')} transaction and all risk indicators)
   - HOW severe the risk is (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the source country ({data.get('source_country')}), destination country ({data.get('destination_country')}), the IP address ({data.get('ip_address', 'N/A')}), KYC status ({data.get('kyc_verified')}), account age ({data.get('account_age_days')} days), and transaction velocity. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""
