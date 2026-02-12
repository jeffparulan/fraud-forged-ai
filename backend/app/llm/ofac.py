"""
OFAC (Office of Foreign Assets Control) country checks for fraud pre-screening.

Cost-efficient pre-checks before expensive LLM calls.
"""
from typing import Dict, Any, List, Tuple

from .config import OFAC_SANCTIONED_COUNTRIES


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
            if is_ofac and country not in countries_found:
                countries_found.append(country)

    return len(countries_found) > 0, countries_found


def build_ofac_risk_warning(data: Dict[str, Any], location_fields: List[str]) -> str:
    """
    Build OFAC risk warning for any sector by checking multiple location fields.

    Args:
        data: Transaction/claim/order data dictionary
        location_fields: List of field names to check for country information

    Returns:
        Warning string if OFAC country found, empty string otherwise
    """
    has_ofac, countries_found = check_ofac_in_data(data, location_fields)

    if has_ofac:
        countries_str = ", ".join(countries_found)
        return f"⚠️ CRITICAL: OFAC SANCTIONED/HIGH-RISK COUNTRY DETECTED - {countries_str}\n" \
               f"Transactions involving {countries_str} are subject to US Treasury OFAC sanctions or are known high-risk fraud countries.\n" \
               f"This is a MAJOR RED FLAG requiring immediate review. Add 40-60 points to fraud score."

    return ""
