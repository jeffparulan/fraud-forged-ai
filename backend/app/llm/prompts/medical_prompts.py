"""Medical fraud detection prompts (single-stage and two-stage)."""
from typing import Dict, Any, Optional, List

from .base_prompts import build_rag_section
from app.llm.ofac import build_ofac_risk_warning


def build_medical_prompt(data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build single-stage fraud detection prompt for medical claims."""
    rag_section = build_rag_section(rag_context)
    ofac_warning = build_ofac_risk_warning(data, ['provider_location', 'patient_location', 'billing_address', 'service_location'])

    return f"""You are a senior healthcare fraud investigator with 15 years of experience in medical billing fraud. Analyze this claim and provide a detailed, professional assessment in plain English. Do NOT generate code or technical syntax.

{rag_section}

CRITICAL FRAUD INDICATORS TO EVALUATE:
{ofac_warning}

Claim Details:
- Claim ID: {data.get('claim_id')}
- Patient Age: {data.get('patient_age')}
- Provider ID: {data.get('provider_id')}
- Specialty: {data.get('specialty')}
- Diagnosis Codes: {data.get('diagnosis_codes')}
- Procedure Codes: {data.get('procedure_codes')}
- Claim Amount: ${data.get('claim_amount')}
- Provider History: {data.get('provider_history')}
- Claim Details: {data.get('claim_details')}

SCORING GUIDELINES (STRICT - be conservative and flag suspicious claims):
- OFAC sanctioned/high-risk countries: Add 40-60 points (CRITICAL if combined with other flags)
- Unbundling (separating procedures that should be billed together): Add 30-40 points
- Upcoding (billing for more expensive procedures): Add 25-35 points
- Procedure/diagnosis mismatch: Add 20-30 points
- Excessive claim amount (> $50,000): Add 15-25 points
- New provider (< 90 days): Add 15-20 points
- Multiple red flags combined: ALWAYS use HIGH (60-85) or CRITICAL (85-100) scores
- IMPORTANT: If 3+ red flags are present (e.g., OFAC country + upcoding + excessive amount), the score MUST be 70+ (HIGH) or 85+ (CRITICAL). Do NOT assign LOW scores when multiple risk indicators are present.

REQUIRED: Provide a comprehensive fraud analysis with:
1. FRAUD_SCORE: A number from 0-100 (be STRICT - multiple red flags should result in HIGH scores of 60-100)
2. RISK_LEVEL: LOW, MEDIUM, HIGH, or CRITICAL
3. RISK_FACTORS: List 3-5 specific red flags (e.g., OFAC country, unbundling, upcoding, procedure mismatch, excessive amount)
4. REASONING: Write 3-4 complete sentences explaining:
   - WHY this claim is suspicious (cite ALL red flags: country, procedure codes, diagnosis codes, billing patterns)
   - WHAT billing patterns indicate fraud (be specific about the ${data.get('claim_amount')} amount and procedure/diagnosis relationships)
   - HOW severe the fraud risk is (combine all factors - multiple red flags = HIGH/CRITICAL risk)
   
Format exactly as:
FRAUD_SCORE: [number]
RISK_LEVEL: [level]
RISK_FACTORS: [factor1, factor2, factor3, factor4, factor5]
REASONING: [Write your detailed analysis here. Reference ALL specific red flags: the claim amount (${data.get('claim_amount')}), the procedure codes ({data.get('procedure_codes')}), diagnosis codes ({data.get('diagnosis_codes')}), and any location-based risks. Be thorough and specific. If multiple red flags are present, assign a HIGH or CRITICAL score.]
"""


def build_stage1_clinical_prompt(data: Dict[str, Any], rag_context: Optional[str] = None) -> str:
    """Build Stage 1 prompt for clinical legitimacy validation (MedGemma)."""
    diag = data.get('diagnosis_codes', [])
    if not diag:
        diag = [data.get('diagnosis_code', 'Unknown')]
    if isinstance(diag, str):
        diag = [d.strip() for d in diag.split(',') if d.strip()]
    diag_str = ', '.join(diag) if diag else 'Unknown'

    proc = data.get('procedure_codes', [])
    if not proc:
        proc = [data.get('procedure_code', 'Unknown')]
    if isinstance(proc, str):
        proc = [p.strip() for p in proc.split(',') if p.strip()]
    proc_str = ', '.join(proc) if proc else 'Unknown'

    prompt = f"""You are a medical expert AI tasked with validating the CLINICAL LEGITIMACY of a medical claim.
Your job is to assess if the medical procedures, diagnoses, and treatments are medically coherent and clinically plausible.

**DO NOT** analyze fraud patterns or billing behavior - that will be done in Stage 2.
**FOCUS ONLY** on clinical validity, medical reasoning, and treatment appropriateness.

Medical Claim Details:
- Claim ID: {data.get('claim_id', 'Unknown')}
- Patient Age: {data.get('patient_age', 'Unknown')} years
- Patient Gender: {data.get('gender', 'Unknown')}
- Provider ID: {data.get('provider_id', 'Unknown')}
- Provider Specialty: {data.get('provider_specialty') or data.get('specialty', 'Unknown')}
- Diagnosis Codes (ICD-10): {diag_str}
- Procedure Codes (CPT): {proc_str}
- Claim Amount: ${data.get('claim_amount', 0):,.2f}
- Treatment Date: {data.get('treatment_date', 'Unknown')}
- Provider History: {data.get('provider_history', 'Unknown')}

Additional Medical Context:
{data.get('claim_details') or data.get('medical_notes', 'No additional notes provided')}

"""
    if rag_context:
        prompt += f"""
Similar Medical Claims (RAG Context):
{rag_context}

"""
    prompt += """
**Clinical Validation Checklist:**
1. **Diagnosis-Procedure Compatibility:** Is the procedure appropriate for the diagnosis? Are ICD-10 and CPT codes medically aligned?
2. **Provider Specialty Match:** Is the provider specialty appropriate for this procedure?
3. **Treatment Timeline Plausibility:** Does the treatment timeline make clinical sense?
4. **Age-Appropriate Care:** Is the treatment appropriate for the patient's age?
5. **Medical Necessity:** Does the diagnosis justify the procedure?

**Response Format (JSON):**
{
  "clinical_legitimacy_score": <0-100, where 0=medically impossible, 100=perfectly coherent>,
  "reasoning": "<Detailed clinical reasoning explaining the score>",
  "risk_factors": ["<List of clinical red flags, if any>"],
  "diagnosis_procedure_match": "<Compatible/Questionable/Incompatible>",
  "provider_specialty_appropriate": "<Yes/Questionable/No>",
  "medical_necessity": "<Clearly Justified/Uncertain/Unjustified>"
}

**Guidelines:** Score 80-100: Clinically coherent. Score 50-79: Some concerns. Score 0-49: Medically questionable.
Focus ONLY on clinical validity, not fraud indicators.

Provide your clinical assessment:"""
    return prompt


def build_stage2_fraud_prompt(
    data: Dict[str, Any],
    rag_context: Optional[str],
    clinical_score: float,
    clinical_reasoning: str,
    clinical_flags: List[str]
) -> str:
    """Build Stage 2 prompt for fraud pattern analysis (Qwen)."""
    diag = data.get('diagnosis_codes', [])
    if not diag:
        diag = [data.get('diagnosis_code', 'Unknown')]
    if isinstance(diag, str):
        diag = [d.strip() for d in diag.split(',') if d.strip()]
    diag_str = ', '.join(diag) if diag else 'Unknown'

    proc = data.get('procedure_codes', [])
    if not proc:
        proc = [data.get('procedure_code', 'Unknown')]
    if isinstance(proc, str):
        proc = [p.strip() for p in proc.split(',') if p.strip()]
    proc_str = ', '.join(proc) if proc else 'Unknown'
    num_services = len(proc) if isinstance(proc, list) else (len(proc.split(',')) if isinstance(proc, str) else data.get('num_services', 1))

    prompt = f"""You are a medical fraud detection AI expert. You have received a clinical legitimacy assessment from a medical expert AI (Stage 1).
Your job is to analyze this claim for FRAUD PATTERNS, BILLING ANOMALIES, and COST MANIPULATION.

**Stage 1 Clinical Validation Results:**
- Clinical Legitimacy Score: {clinical_score}/100
- Clinical Assessment: {clinical_reasoning}
- Clinical Red Flags: {', '.join(clinical_flags) if clinical_flags else 'None'}

**Medical Claim Details:**
- Claim ID: {data.get('claim_id', 'Unknown')}
- Patient Age: {data.get('patient_age', 'Unknown')} years
- Provider ID: {data.get('provider_id', 'Unknown')}
- Provider Specialty: {data.get('provider_specialty') or data.get('specialty', 'Unknown')}
- Diagnosis Codes (ICD-10): {diag_str}
- Procedure Codes (CPT): {proc_str}
- Claim Amount: ${data.get('claim_amount', 0):,.2f}
- Number of Services: {num_services}
- Claim Details: {data.get('claim_details', 'No additional details')}

**Billing Context:**
- Average Peer Cost: ${data.get('peer_average_cost', 0):,.2f}
- Provider's Past Claims (last 30 days): {data.get('provider_claim_count_30d', 'Unknown')}
- Patient's Past Claims (last 90 days): {data.get('patient_claim_count_90d', 'Unknown')}

"""
    if rag_context:
        prompt += f"""
**Similar Fraud Patterns (RAG Context):**
{rag_context}

"""
    prompt += """
**CRITICAL: You MUST respond in valid JSON format. The fraud_score MUST be a number between 0-100 (NOT a percentage).**

**Response Format (JSON):**
```json
{
  "fraud_score": <0-100>,
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "reasoning": "<Detailed fraud analysis>",
  "risk_factors": ["<List of specific fraud indicators>"],
  "fraud_type": "<Upcoding/Unbundling/Phantom/Kickback/None>",
  "recommended_action": "<Approve/Flag for Review/Deny/Investigate>"
}
```

**Scoring Guidelines:** 0-25 LOW, 26-50 MEDIUM, 51-75 HIGH, 76-100 CRITICAL.
Factor in Stage 1 clinical score heavily. Low clinical legitimacy (< 50) should raise fraud score significantly.

Provide your fraud analysis:"""
    return prompt
