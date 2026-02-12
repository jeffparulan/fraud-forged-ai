"""Supply chain fraud detection prompts."""
from typing import Dict, Any, Optional

from .base_prompts import build_rag_section
from app.llm.ofac import build_ofac_risk_warning


def build_supply_chain_prompt(data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build fraud detection prompt for supply chain sector."""
    rag_section = build_rag_section(rag_context)
    ofac_warning = build_ofac_risk_warning(data, ['supplier_location', 'supplier_country', 'origin_country', 'shipping_location', 'billing_address'])

    doc_complete = data.get('documentation_complete', False)
    reg_compliance = data.get('regulatory_compliance', False)
    compliance_risk = ""
    if not doc_complete:
        compliance_risk += "⚠️ WARNING: Documentation incomplete - Missing documentation is a HIGH-RISK indicator for fraud!\n"
    if not reg_compliance:
        compliance_risk += "⚠️ WARNING: Regulatory compliance issues - Non-compliance is a HIGH-RISK indicator!\n"

    return f"""You are a senior supply chain fraud investigator with expertise in procurement fraud, kickback schemes, and ghost suppliers. Analyze this order and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}{compliance_risk}

Order Details:
- Supplier ID: {data.get('supplier_id', 'N/A')}
- Supplier Name: {data.get('supplier_name', 'N/A')}
- Order Amount: ${data.get('order_amount', 'N/A')}
- Order Frequency: {data.get('order_frequency', 'N/A')} per year
- Payment Terms: {data.get('payment_terms', 'N/A')}
- Supplier Age: {data.get('supplier_age_days', 'N/A')} days (NEW suppliers < 90 days are HIGH RISK)
- Price Variance: {data.get('price_variance', 'N/A')}% from market average
- Delivery Variance: {data.get('delivery_variance', 'N/A')}%
- Quality Issues: {data.get('quality_issues', 'N/A')}
- Documentation Complete: {data.get('documentation_complete', False)} (FALSE = HIGH RISK)
- Regulatory Compliance: {data.get('regulatory_compliance', False)} (FALSE = HIGH RISK)
- Order Details: {data.get('order_details', 'N/A')}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious orders):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Ghost supplier (new, no history): Add 30-40 points
- Price variance > 30%: Add 25-35 points
- Missing documentation: Add 20-30 points
- Regulatory non-compliance: Add 25-35 points
- Quality issues: Add 15-25 points
- Large order amount (> $100,000): Add 15-25 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present, the score MUST be 70+ (HIGH) or 85+ (CRITICAL).

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, ghost supplier, price variance, missing docs, compliance issues)
4. REASONING: Write 3-4 complete sentences explaining WHY this supplier is suspicious, WHAT procurement fraud patterns are present, HOW severe the fraud risk is.
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags. Be thorough and specific.]
"""
