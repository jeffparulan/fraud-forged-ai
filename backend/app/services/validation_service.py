"""
Fraud validation and pre-check services.

Contains OFAC country checks, extreme fraud pattern detection,
and other validation logic that doesn't require LLM inference.
"""
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# OFAC (Office of Foreign Assets Control) Sanctioned Countries and High-Risk Fraud Countries
# Based on US Treasury OFAC sanctions and high-risk fraud patterns
OFAC_SANCTIONED_COUNTRIES = [
    # Fully sanctioned countries (comprehensive sanctions)
    'cuba', 'iran', 'north korea', 'syria', 'crimea', 'donetsk', 'luhansk',
    # Countries with significant sanctions
    'russia', 'belarus', 'venezuela', 'myanmar', 'burma', 'sudan', 'south sudan',
    'libya', 'yemen', 'somalia', 'central african republic', 'democratic republic of congo',
    'congo', 'zimbabwe', 'mali', 'burkina faso', 'niger',
    # High-risk fraud countries (not OFAC but high fraud rates)
    'nigeria', 'ghana', 'cameroon', 'ivory coast', 'senegal', 'togo', 'benin',
    'philippines', 'indonesia', 'malaysia', 'thailand', 'vietnam', 'pakistan',
    'bangladesh', 'romania', 'bulgaria', 'ukraine', 'moldova', 'albania',
    'serbia', 'bosnia', 'macedonia', 'montenegro', 'kosovo',
    # Additional high-risk regions
    'west africa', 'east africa', 'balkans', 'eastern europe'
]


def check_ofac_country(location_str: str) -> Tuple[bool, str]:
    """
    Check if a location string contains OFAC sanctioned or high-risk countries.
    
    Args:
        location_str: Location string to check (country name, address, etc.)
    
    Returns:
        Tuple of (is_ofac_country: bool, country_found: str)
    """
    if not location_str:
        return False, ""
    
    location_lower = str(location_str).lower()
    
    for country in OFAC_SANCTIONED_COUNTRIES:
        if country in location_lower:
            return True, country.title()
    
    return False, ""


def check_ofac_in_data(data: Dict[str, Any], location_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if any OFAC countries are present in the data (cost-efficient pre-check).
    
    Args:
        data: Transaction/claim/order data dictionary
        location_fields: List of field names to check for country information
    
    Returns:
        Tuple of (has_ofac: bool, countries_found: List[str])
    """
    countries_found = []
    
    for field in location_fields:
        field_value = data.get(field, "")
        if field_value:
            is_ofac, country = check_ofac_country(str(field_value))
            if is_ofac:
                countries_found.append(f"{country} (field: {field})")
    
    return len(countries_found) > 0, countries_found


def build_ofac_risk_warning(data: Dict[str, Any], location_fields: List[str]) -> str:
    """
    Build a risk warning message for OFAC country detection.
    
    Args:
        data: Transaction/claim/order data dictionary
        location_fields: List of field names to check
    
    Returns:
        Formatted risk warning string
    """
    has_ofac, countries = check_ofac_in_data(data, location_fields)
    
    if not has_ofac:
        return ""
    
    warning = "⚠️ OFAC/HIGH-RISK COUNTRY DETECTED:\n"
    for country_info in countries:
        warning += f"  • {country_info}\n"
    
    warning += "\nRISK FACTORS:\n"
    warning += "  • Transaction from sanctioned or high-risk fraud region\n"
    warning += "  • Elevated risk of fraud, money laundering, or sanctions violations\n"
    warning += "  • Recommend immediate enhanced due diligence (EDD)\n"
    
    return warning


def check_extreme_fraud_patterns(sector: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check for extreme fraud patterns that warrant immediate HIGH/CRITICAL scores.
    This is a cost-efficient pre-check before calling expensive LLM inference.
    
    Returns None if no extreme patterns found, otherwise returns fraud result dict.
    """
    # Define sector-specific location fields
    sector_location_fields = {
        "banking": ["location", "ip_location", "origin_country"],
        "medical": ["location", "provider_location", "facility_location"],
        "ecommerce": ["shipping_location", "shipping_address", "billing_address", "origin_country"],
        "supply_chain": ["supplier_location", "supplier_country", "origin_country", "shipping_location", "billing_address"]
    }
    
    location_fields = sector_location_fields.get(sector, [])
    has_ofac, ofac_countries = check_ofac_in_data(data, location_fields)
    
    if has_ofac:
        # OFAC country detected - check for additional red flags
        red_flags_count = 0
        risk_factors = []
        
        # Add OFAC detection to risk factors
        risk_factors.append(f"OFAC/High-Risk Countries: {', '.join(ofac_countries)}")
        red_flags_count += len(ofac_countries)
        
        # Sector-specific additional checks
        if sector == "banking":
            if data.get("large_transaction", False) or data.get("amount", 0) > 50000:
                red_flags_count += 1
                risk_factors.append("Large transaction from high-risk region")
        elif sector == "ecommerce":
            if not data.get("email_verified", False):
                red_flags_count += 1
                risk_factors.append("Unverified email")
        elif sector == "supply_chain":
            if not data.get("documentation_complete", False):
                red_flags_count += 1
                risk_factors.append("Missing documentation")
        
        # Check for new accounts/sellers/suppliers
        age_field = {
            "banking": "account_age_days",
            "ecommerce": "seller_age_days",
            "supply_chain": "supplier_age_days"
        }.get(sector)
        
        if age_field and data.get(age_field, 365) < 30:
            red_flags_count += 1
            risk_factors.append(f"New {sector.replace('_', ' ')} (< 30 days)")
        
        # If OFAC + 2+ other red flags, return immediately (save LLM costs)
        if red_flags_count >= 2:
            logger.warning(f"🚨 [Pre-Check] OFAC country + {red_flags_count-1} red flags detected - skipping LLM inference")
            ofac_warning = build_ofac_risk_warning(data, location_fields)
            
            return {
                "fraud_score": 95.0,  # CRITICAL
                "risk_level": "CRITICAL",
                "explanation": f"CRITICAL FRAUD ALERT - Pre-LLM Check\n\n{ofac_warning}\nADDITIONAL RED FLAGS:\n" + "\n".join(f"  • {rf}" for rf in risk_factors[1:]),
                "model_used": "Pre-Check (OFAC Detection + Rule-Based)",
                "provider": "deterministic",
                "reasoning": "Transaction from OFAC-sanctioned or high-risk fraud country with multiple additional red flags. Immediate review required.",
            }
    
    # Check for extreme values in specific sectors
    base_score = None
    risk_factors = []
    
    if sector == "ecommerce":
        try:
            listed_price = float(data.get("listed_price", 0))
            market_price = float(data.get("market_price", 0))
            
            if market_price > 0 and listed_price > 0:
                markup_ratio = listed_price / market_price
                markup_percent = (markup_ratio - 1) * 100
                
                # CRITICAL: >1000% markup
                if markup_percent > 1000:
                    base_score = 95
                    risk_factors.append(f"Extreme price markup: {markup_percent:.0f}% above market")
                # HIGH: >500% markup
                elif markup_percent > 500:
                    base_score = 85
                    risk_factors.append(f"Very high price markup: {markup_percent:.0f}% above market")
                
                # Check for negative reviews
                if data.get("seller_rating", 5.0) < 2.0:
                    base_score = max(base_score or 0, 75)
                    risk_factors.append(f"Poor seller rating: {data.get('seller_rating', 'N/A')}/5.0")
                
                if base_score:
                    logger.warning(f"🚨 [Pre-Check] Extreme e-commerce fraud pattern detected - score: {base_score}")
                    risk_level = _get_risk_level(base_score)
                    
                    return {
                        "fraud_score": base_score,
                        "risk_level": risk_level,
                        "explanation": f"{risk_level} FRAUD ALERT - Pre-LLM Check\n\nRED FLAGS:\n" + "\n".join(f"  • {rf}" for rf in risk_factors),
                        "model_used": "Pre-Check (Rule-Based)",
                        "provider": "deterministic",
                        "reasoning": "Extreme fraud indicators detected before LLM analysis. Immediate review recommended.",
                    }
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse prices for pre-check: {e}")
    
    elif sector == "supply_chain":
        try:
            price_variance = float(data.get("price_variance", 0))
            
            # CRITICAL: >500% price variance
            if price_variance > 500:
                base_score = 90
                risk_factors.append(f"Extreme price variance: {price_variance}%")
            # HIGH: >300% price variance
            elif price_variance > 300:
                base_score = 80
                risk_factors.append(f"Very high price variance: {price_variance}%")
            
            if base_score:
                logger.warning(f"🚨 [Pre-Check] Extreme supply chain fraud pattern detected - score: {base_score}")
                risk_level = _get_risk_level(base_score)
                
                return {
                    "fraud_score": base_score,
                    "risk_level": risk_level,
                    "explanation": f"{risk_level} FRAUD ALERT - Pre-LLM Check\n\nRED FLAGS:\n" + "\n".join(f"  • {rf}" for rf in risk_factors),
                    "model_used": "Pre-Check (Rule-Based)",
                    "provider": "deterministic",
                    "reasoning": "Extreme fraud indicators detected before LLM analysis. Immediate review recommended.",
                }
        except (ValueError, TypeError) as e:
            logger.debug(f"Could not parse price variance for pre-check: {e}")
    
    # No extreme patterns found - proceed with LLM inference
    return None


def _get_risk_level(fraud_score: float) -> str:
    """Determine risk level from fraud score."""
    if fraud_score < 30:
        return 'LOW'
    elif fraud_score < 60:
        return 'MEDIUM'
    elif fraud_score < 85:
        return 'HIGH'
    else:
        return 'CRITICAL'
