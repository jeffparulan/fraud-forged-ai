"""
LLM response parsing for fraud detection and clinical validation.
"""
import re
import json
import logging

logger = logging.getLogger(__name__)


def get_risk_level(fraud_score: float) -> str:
    """Calculate risk level from fraud score."""
    if fraud_score < 30:
        return "LOW"
    elif fraud_score < 60:
        return "MEDIUM"
    elif fraud_score < 85:
        return "HIGH"
    else:
        return "CRITICAL"


def clean_reasoning(text: str) -> str:
    """Clean up reasoning text by removing code artifacts, regex, and shell commands."""
    # Remove FRAUD_SCORE and RISK_LEVEL statements (they're displayed separately)
    text = re.sub(r'FRAUD[_\s]SCORE:\s*\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'RISK[_\s]LEVEL:\s*(LOW|MEDIUM|HIGH|CRITICAL)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'RISK[_\s]FACTORS:\s*[^\n]*', '', text, flags=re.IGNORECASE)

    # If the text contains "Code:" or code markers, this is likely a bad response
    if re.search(r'\bCode:\s*```|```python|```javascript|import\s+\w+|def\s+\w+\(', text, re.IGNORECASE):
        match = re.search(r'^([^`#]+?)(?:\s*Code:|```|import|def|class)', text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            return "The transaction shows fraud risk based on multiple indicators including transaction amount, account age, and geographic location."

    # Remove shell commands and pipes
    text = re.sub(r'\s*\|\s*\w+\s+[\'"].*?[\'"]', '', text)
    text = re.sub(r'[\'"]s/.*?/.*?/[gi]*[\'"]', '', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'(?:import|from)\s+\w+.*', '', text)
    text = re.sub(r'def\s+\w+\(.*?\):', '', text)
    text = re.sub(r'#\s*\w+.*', '', text)
    text = re.sub(r'["\']$', '', text)
    text = re.sub(r'\s*\)\s*$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\b(Example|Reasoning|Analysis):\s*', '', text, flags=re.IGNORECASE)

    if len(text) < 50:
        return "This transaction exhibits fraud risk based on the transaction details, account age, and geographic factors provided."

    if text and text[-1] not in '.!?':
        if len(text) > 100:
            text += '.'

    return text


def parse_model_response(
    text: str,
    sector: str,
    data: dict,
    is_clinical_stage: bool = False
) -> dict:
    """
    Parse LLM response to extract structured fraud analysis or clinical validation.

    Args:
        text: Raw LLM response text
        sector: sector name
        data: transaction/claim data
        is_clinical_stage: If True, parse as clinical legitimacy validation (Stage 1)

    Returns:
        Parsed dict with fraud_score/clinical_legitimacy_score, risk_level, risk_factors, reasoning
    """
    if is_clinical_stage:
        return _parse_clinical_response(text)

    return _parse_fraud_response(text)


def _parse_clinical_response(text: str) -> dict:
    """Parse Stage 1 clinical legitimacy validation response."""
    json_match = re.search(r'\{[^}]*"clinical_legitimacy_score"[^}]*\}', text, re.DOTALL)
    if json_match:
        try:
            parsed_json = json.loads(json_match.group(0))
            return {
                "clinical_legitimacy_score": parsed_json.get("clinical_legitimacy_score", 50),
                "reasoning": parsed_json.get("reasoning", text),
                "risk_factors": parsed_json.get("risk_factors", []),
                "diagnosis_procedure_match": parsed_json.get("diagnosis_procedure_match", "Unknown"),
                "provider_specialty_appropriate": parsed_json.get("provider_specialty_appropriate", "Unknown"),
                "medical_necessity": parsed_json.get("medical_necessity", "Unknown")
            }
        except json.JSONDecodeError:
            pass

    score_match = re.search(r'clinical[_\s]legitimacy[_\s]score["\']?\s*:\s*(\d+)', text, re.IGNORECASE)
    if score_match:
        clinical_score = int(score_match.group(1))
    else:
        pct_match = re.search(r'(\d+)\s*(?:%|out of 100|/100)', text, re.IGNORECASE)
        if pct_match:
            clinical_score = int(pct_match.group(1))
        else:
            text_lower = text.lower()
            if any(w in text_lower for w in ['appropriate', 'coherent', 'standard', 'normal', 'typical', 'reasonable']):
                clinical_score = 85 if any(w in text_lower for w in ['highly', 'very', 'completely', 'fully']) else \
                    70 if any(w in text_lower for w in ['somewhat', 'mostly', 'generally']) else 75
            elif any(w in text_lower for w in ['inappropriate', 'incompatible', 'unusual', 'concerning', 'red flag']):
                clinical_score = 15 if any(w in text_lower for w in ['highly', 'very', 'completely', 'definitely']) else \
                    40 if any(w in text_lower for w in ['somewhat', 'possibly', 'potentially']) else 30
            elif any(w in text_lower for w in ['insufficient', 'limited', 'unclear', 'unknown', 'impossible']):
                clinical_score = 25
            else:
                clinical_score = 50

    reasoning_match = re.search(r'["\']?reasoning["\']?\s*:\s*["\'](.+?)["\']', text, re.IGNORECASE | re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else text

    factors_match = re.search(r'["\']?risk[_\s]factors["\']?\s*:\s*\[([^\]]+)\]', text, re.IGNORECASE)
    risk_factors = [f.strip(' "\'') for f in factors_match.group(1).split(',')] if factors_match else []

    return {
        "clinical_legitimacy_score": clinical_score,
        "reasoning": clean_reasoning(reasoning),
        "risk_factors": risk_factors,
        "diagnosis_procedure_match": "Unknown",
        "provider_specialty_appropriate": "Unknown",
        "medical_necessity": "Unknown"
    }


def _parse_fraud_response(text: str) -> dict:
    """Parse Stage 2 / single-stage fraud detection response."""
    json_patterns = [
        r'```json\s*(\{.*?"fraud_score".*?\})\s*```',
        r'```\s*(\{.*?"fraud_score".*?\})\s*```',
        r'(\{.*?"fraud_score".*?\})',
    ]

    fraud_score = None
    for pattern in json_patterns:
        json_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if json_match:
            try:
                parsed_json = json.loads(json_match.group(1).strip())
                fraud_score = parsed_json.get("fraud_score")
                if fraud_score is not None:
                    fraud_score = max(0, min(100, int(fraud_score)))
                    logger.info(f"✅ Extracted fraud_score from JSON: {fraud_score}")
                    break
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    if fraud_score is None:
        score_match = re.search(r'FRAUD[_\s]SCORE["\']?\s*:\s*(\d+)', text, re.IGNORECASE)
        if score_match:
            fraud_score = int(score_match.group(1))
            logger.info(f"✅ Extracted fraud_score from FRAUD_SCORE pattern: {fraud_score}")
        else:
            pct_matches = re.findall(r'(\d+)\s*%', text)
            valid_scores = [int(m) for m in pct_matches if 0 <= int(m) <= 100]
            fraud_score = valid_scores[0] if valid_scores else 50
            if valid_scores:
                logger.info(f"✅ Extracted fraud_score from percentage: {fraud_score}")
            else:
                for pattern in [r'["\']?score["\']?\s*:\s*(\d+)', r'score\s+of\s+(\d+)', r'score\s+(\d+)']:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        candidate = int(match.group(1))
                        if 0 <= candidate <= 100:
                            fraud_score = candidate
                            break
                if fraud_score is None:
                    fraud_score = 50
                    logger.warning(f"⚠️  Could not extract fraud_score, using default: {fraud_score}")

    fraud_score = max(0, min(100, int(fraud_score)))
    risk_level = get_risk_level(fraud_score)

    factors_match = re.search(r'RISK[_\s]FACTORS:\s*([^\n]+)', text, re.IGNORECASE)
    risk_factors = [f.strip() for f in factors_match.group(1).split(',')] if factors_match else ['Analysis pending']

    reasoning_match = re.search(r'REASONING:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
    reasoning = reasoning_match.group(1).strip() if reasoning_match else text
    reasoning = clean_reasoning(reasoning)

    if len(reasoning) > 1200:
        last_period = max(
            reasoning[:1200].rfind('.'), reasoning[:1200].rfind('!'), reasoning[:1200].rfind('?')
        )
        reasoning = reasoning[:last_period + 1] if last_period > 150 else reasoning[:1200]

    if reasoning and reasoning.rstrip().endswith((' is', ' are', ' was', ' were', ' has', ' have', ' the')):
        prev_period = max(
            reasoning[:-10].rfind('.'), reasoning[:-10].rfind('!'), reasoning[:-10].rfind('?')
        )
        if prev_period > 150:
            reasoning = reasoning[:prev_period + 1]

    return {
        'fraud_score': fraud_score,
        'risk_level': risk_level,
        'risk_factors': risk_factors,
        'reasoning': reasoning
    }
