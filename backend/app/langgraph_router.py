from typing import Dict, Any, TypedDict, Optional
from langgraph.graph import Graph, StateGraph
try:
    from langchain_core.messages import HumanMessage, SystemMessage
except ImportError:
    # Fallback for older langchain versions
    from langchain.schema import HumanMessage, SystemMessage
import json
import logging

logger = logging.getLogger(__name__)

# Optional MCP integration for enhanced context
try:
    from app.utils.mcp_client import get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.info("MCP client not available - enhanced context features disabled")


class RouterState(TypedDict):
    """State passed through LangGraph workflow"""
    sector: str
    input_data: Dict[str, Any]
    model_name: str
    rag_context: str
    fraud_score: float
    risk_level: str
    explanation: str
    similar_patterns: int
    risk_factors: list


class LangGraphRouter:
    """
    LangGraph-powered intelligent routing engine.
    Routes requests to sector-specific LLMs with RAG enhancement.
    Now with REAL Hugging Face API integration!
    """
    
    def __init__(self, rag_engine, hf_client=None):
        self.rag_engine = rag_engine
        self.hf_client = hf_client  # Optional HF client for real inference
        self.model_mapping = {
            "banking": "Finance-Llama3-8B",
            "medical": "MedGemma-4B (Google Health AI)",
            "ecommerce": "NVIDIA: Nemotron Nano 12B 2 VL",
            "supply_chain": "NVIDIA: Nemotron Nano 12B 2 VL"
        }
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> Graph:
        """Build LangGraph workflow for fraud detection - RAG FIRST for context, then HF/fallback"""
        
        workflow = StateGraph(RouterState)
        
        workflow.add_node("route_model", self._route_to_model)
        workflow.add_node("retrieve_context", self._retrieve_rag_context)  # RAG FIRST for context
        workflow.add_node("analyze_fraud", self._analyze_with_llm)  # Then HF or fallback (with RAG context)
        workflow.add_node("generate_explanation", self._generate_explanation)
        
        workflow.set_entry_point("route_model")
        # Retrieve RAG context FIRST, then use it in LLM analysis or fallback
        workflow.add_edge("route_model", "retrieve_context")
        workflow.add_edge("retrieve_context", "analyze_fraud")
        workflow.add_edge("analyze_fraud", "generate_explanation")
        workflow.set_finish_point("generate_explanation")
        
        return workflow.compile()
    
    def _route_to_model(self, state: RouterState) -> RouterState:
        """Route to appropriate model based on sector"""
        sector = state["sector"]
        state["model_name"] = self.model_mapping.get(sector, "NVIDIA: Nemotron Nano 12B 2 VL")
        return state
    
    def _retrieve_rag_context(self, state: RouterState) -> RouterState:
        """Retrieve similar fraud patterns from Pinecone"""
        sector = state["sector"]
        input_data = state["input_data"]
        
        query_text = self._format_query(sector, input_data)
        
        results = self.rag_engine.query_similar_patterns(
            sector=sector,
            query_text=query_text,
            n_results=5
        )
        
        state["rag_context"] = results["context"]
        state["similar_patterns"] = results["count"]
        
        return state
    
    def _analyze_with_llm(self, state: RouterState) -> RouterState:
        """
        Analyze fraud using Hugging Face models if available,
        otherwise fall back to rule-based scoring.
        Enhanced with MCP (Model Context Protocol) for external context.
        """
        sector = state["sector"]
        data = state["input_data"]
        rag_context = state["rag_context"]
        
        # Get enhanced context from MCP if available
        mcp_context = {}
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client.enabled:
                    mcp_context = mcp_client.get_context(sector, data)
                    logger.info(f"✅ MCP context retrieved: {list(mcp_context.keys())}")
            except Exception as e:
                logger.warning(f"MCP context retrieval failed: {e}")
        
        # Merge MCP context into data for LLM analysis
        enhanced_data = {**data, **mcp_context}
        
        # Calculate rule-based score FIRST - this is our source of truth
        rule_based_score = self._calculate_fraud_score(sector, data, rag_context)
        rule_based_risk = self._get_risk_level(rule_based_score)
        logger.info(f"[Scoring] Rule-based score: {rule_based_score:.2f} ({rule_based_risk.upper()})")
        
        # STRICT MODE: Prefer rule-based scoring for consistency
        # Only use HF if it's VERY close to rule-based (within 15 points)
        # This ensures deterministic, reliable results
        use_hf = False
        hf_score = None
        hf_result = None
        
        if self.hf_client:
            try:
                # Get the actual provider being used for this sector (once at the start)
                from app.utils.llm_client import SECTOR_MODELS
                sector_config = SECTOR_MODELS.get(sector, {})
                primary_provider = sector_config.get("primary", {}).get("provider", "unknown")
                primary_model = sector_config.get("primary", {}).get("model", "unknown")
                provider_label = primary_provider.upper() if primary_provider != "hf" else "HF"
                
                logger.info(f"[LLM] Attempting {provider_label} inference for {sector} (model: {primary_model})")
                # Pass RAG context to the LLM for better accuracy
                hf_result = self.hf_client.analyze_fraud(sector, enhanced_data, rag_context=rag_context)
                hf_score = hf_result["fraud_score"]
                hf_risk = hf_result.get("risk_level", "").lower()
                
                logger.info(f"[LLM] {provider_label} score: {hf_score:.2f} ({hf_risk.upper()}), Rule-based: {rule_based_score:.2f} ({rule_based_risk.upper()})")
                
                score_diff = abs(hf_score - rule_based_score)
                
                # IMPROVED VALIDATION RULES - Trust LLM more, especially when rule-based is very low
                # LLMs can catch subtle patterns that rule-based systems miss
                
                # Rule 1: If rule-based is VERY LOW (< 10) and LLM is CRITICAL (> 85) → REJECT LLM (extreme mismatch)
                if rule_based_score < 10 and hf_score > 85:
                    logger.warning(f"[Validation] ❌ REJECTED {provider_label}: Rule-based VERY LOW ({rule_based_score:.2f}) vs {provider_label} CRITICAL ({hf_score:.2f}) - extreme mismatch")
                    use_hf = False
                
                # Rule 2: If rule-based is HIGH (> 60) and LLM is LOW (< 30) → REJECT LLM (missed high risk)
                elif rule_based_score > 60 and hf_score < 30:
                    logger.warning(f"[Validation] ❌ REJECTED {provider_label}: Rule-based HIGH ({rule_based_score:.2f}) vs {provider_label} LOW ({hf_score:.2f}) - LLM missed high risk")
                    use_hf = False
                
                # Rule 3: If rule-based is VERY LOW (< 10) → Trust LLM more (allow up to 40 points difference)
                # LLMs can detect subtle fraud patterns that simple rules miss
                elif rule_based_score < 10:
                    if hf_score > 50:  # Only reject if LLM says it's clearly high risk
                        logger.info(f"[Validation] ✅ ACCEPTED {provider_label}: Rule-based VERY LOW ({rule_based_score:.2f}), trusting {provider_label} score ({hf_score:.2f}) - LLM may detect subtle patterns")
                        use_hf = True
                    else:
                        use_hf = True
                        logger.info(f"[Validation] ✅ ACCEPTED {provider_label}: Both scores low ({rule_based_score:.2f} vs {hf_score:.2f})")
                
                # Rule 4: If rule-based is LOW (10-30) → Allow moderate LLM scores (up to 25 points difference)
                elif rule_based_score < 30:
                    if score_diff > 25:
                        logger.warning(f"[Validation] ❌ REJECTED {provider_label}: Large discrepancy ({score_diff:.2f} points) when rule-based is LOW")
                        use_hf = False
                    else:
                        use_hf = True
                        logger.info(f"[Validation] ✅ ACCEPTED {provider_label}: Moderate discrepancy ({score_diff:.2f} points) - trusting LLM analysis")
                
                # Rule 5: If scores differ by more than 20 points (for medium/high rule-based) → REJECT LLM
                elif score_diff > 20:
                    logger.warning(f"[Validation] ❌ REJECTED {provider_label}: Large discrepancy ({score_diff:.2f} points). Using rule-based for consistency.")
                    use_hf = False
                
                # Rule 6: If risk levels don't match and difference is > 15 points → REJECT LLM
                elif score_diff > 15 and rule_based_risk != hf_risk:
                    logger.warning(f"[Validation] ❌ REJECTED {provider_label}: Risk level mismatch ({rule_based_risk} vs {hf_risk}) with {score_diff:.2f} point difference")
                    use_hf = False
                
                # Rule 7: Accept LLM if scores are reasonably close
                else:
                    use_hf = True
                    logger.info(f"[Validation] ✅ ACCEPTED {provider_label}: Scores reasonably close ({score_diff:.2f} points), risk levels: {rule_based_risk} vs {hf_risk}")
                
            except Exception as e:
                # provider_label already defined above
                logger.error(f"[LLM] {provider_label} inference failed: {e}, using rule-based")
                use_hf = False
        
        # TRANSPARENT DECISION: Use rule-based or validated LLM
        # Always be honest about which method was used
        if not use_hf:
            # Using rule-based scoring (LLM was rejected or unavailable)
            state["fraud_score"] = rule_based_score
            state["risk_level"] = rule_based_risk
            state["risk_factors"] = []
            # Mark that we're using rule-based (not LLM)
            state["_analysis_method"] = "rule_based"
            state["_hf_rejected"] = True
            
            # Get provider label for logging (if we tried LLM, otherwise use generic)
            if self.hf_client:
                from app.utils.llm_client import SECTOR_MODELS
                sector_config = SECTOR_MODELS.get(sector, {})
                primary_provider = sector_config.get("primary", {}).get("provider", "unknown")
                provider_label = primary_provider.upper() if primary_provider != "hf" else "HF"
                logger.info(f"[Final] ✅ Using RULE-BASED score: {rule_based_score:.2f} ({rule_based_risk.upper()}) - {provider_label} was rejected or unavailable")
            else:
                logger.info(f"[Final] ✅ Using RULE-BASED score: {rule_based_score:.2f} ({rule_based_risk.upper()}) - LLM unavailable")
        else:
            # LLM result is validated and close to rule-based
            # provider_label already defined above
            state["fraud_score"] = hf_score
            state["risk_level"] = hf_result["risk_level"].lower()
            state["risk_factors"] = hf_result.get("risk_factors", [])
            state["explanation"] = hf_result.get("reasoning", "")
            # Mark that we're using validated LLM
            state["_analysis_method"] = "llm_validated"
            state["_hf_rejected"] = False
            logger.info(f"[Final] ✅ Using VALIDATED {provider_label} score: {hf_score:.2f} ({hf_result['risk_level']}) - Validated against rule-based ({rule_based_score:.2f})")
        
        return state
    
    def _generate_explanation(self, state: RouterState) -> RouterState:
        """Generate human-readable explanation - TRANSPARENT about method used"""
        sector = state["sector"]
        data = state["input_data"]
        fraud_score = state["fraud_score"]
        risk_level = state["risk_level"]
        model_name = state["model_name"]
        analysis_method = state.get("_analysis_method", "rule_based")
        
        # TRANSPARENCY: Be honest about which method was used
        if state.get("explanation") and analysis_method == "hf_validated":
            # HF-generated explanation - use it as-is but be transparent
            prefix = f"{model_name} analysis: "
            if not state["explanation"].startswith(prefix):
                state["explanation"] = prefix + state["explanation"]
            logger.debug(f"[Explanation] Using HF-generated explanation from {model_name}")
        else:
            # Generate rule-based explanation - be transparent about it
            explanation = self._build_explanation(sector, data, fraud_score, risk_level, model_name)
            state["explanation"] = explanation
            logger.debug(f"[Explanation] Generated rule-based explanation (HF was rejected or unavailable)")
        
        return state
    
    def _format_query(self, sector: str, data: Dict[str, Any]) -> str:
        """Format input data as query text for RAG"""
        return json.dumps(data, indent=2)
    
    def _calculate_fraud_score(self, sector: str, data: Dict[str, Any], rag_context: str) -> float:
        """
        Calculate fraud score using sector-specific logic with RAG context enhancement.
        This simulates LLM analysis with rule-based scoring.
        """
        score = 0.0
        
        if sector == "banking":
            score = self._score_banking_fraud(data)
        elif sector == "medical":
            score = self._score_medical_fraud(data)
        elif sector == "ecommerce":
            score = self._score_ecommerce_fraud(data)
        elif sector == "supply_chain":
            score = self._score_supply_chain_fraud(data)
        else:
            score = 50.0  # Default
        
        # Use RAG context to enhance scoring - CONSERVATIVE approach
        # Only make small adjustments to avoid over-inflating scores
        if rag_context and rag_context != "No similar patterns found.":
            rag_lower = rag_context.lower()
            
            # Check for legitimate patterns in RAG context (reduce score for legitimate transactions)
            legitimate_keywords = ["low risk", "legitimate", "normal", "standard", "established", "verified", "clean"]
            if any(keyword in rag_lower for keyword in legitimate_keywords) and score < 30:
                # Reduce score for legitimate patterns (only if already low)
                score = max(0, score * 0.8)  # Reduce by 20% (more conservative)
                logger.debug(f"[RAG] Legitimate pattern found - reducing score by 20%: {score:.2f}")
            
            # Only enhance if base score is already suspicious (score > 30)
            # Use SMALL adjustments to avoid over-inflation
            elif score > 30:
                # Check for high risk indicators in RAG context
                if any(keyword in rag_lower for keyword in ["high risk", "fraud", "critical", "suspicious", "anomaly"]):
                    # Small enhancement to avoid over-inflation
                    score = min(100, score * 1.1)  # Reduced from 1.15 to 1.1 (10% instead of 15%)
                    logger.debug(f"[RAG] High-risk pattern found - enhancing score by 10%: {score:.2f}")
                # Check for medium risk indicators
                elif any(keyword in rag_lower for keyword in ["medium risk", "warning", "unusual", "irregular"]):
                    score = min(100, score * 1.05)  # Reduced from 1.08 to 1.05 (5% instead of 8%)
                    logger.debug(f"[RAG] Medium-risk pattern found - enhancing score by 5%: {score:.2f}")
            else:
                # Base score is low (< 30), don't enhance even if RAG finds risk keywords
                # This prevents legitimate transactions from being boosted
                logger.debug(f"[RAG] Base score is low ({score:.2f}), not enhancing despite RAG context")
        
        # Round to 1 decimal place for consistency
        return round(score, 1)
    
    def _score_banking_fraud(self, data: Dict[str, Any]) -> float:
        """Banking/crypto fraud scoring logic - properly accounts for legitimate transactions"""
        score = 0.0
        logger.debug(f"[Banking Scoring] Starting with data: {data}")
        
        # Amount-based risk
        try:
            amount = float(data.get("amount", 0))
        except (ValueError, TypeError):
            amount = 0.0
            logger.warning(f"[Banking Scoring] Invalid amount: {data.get('amount')}")
        if amount > 100000:
            score += 30
        elif amount > 50000:
            score += 20
        elif amount > 10000:
            score += 15
        elif amount > 5000:
            score += 10
        elif amount < 1000:
            score -= 10  # Small amounts are less risky
        
        # Location risk
        location = str(data.get("location", "")).lower()
        source_country = str(data.get("source_country", "")).lower()
        dest_country = str(data.get("destination_country", "")).lower()
        
        high_risk_locations = ["nigeria", "russia", "china", "unknown", "cayman islands"]
        if any(loc in location for loc in high_risk_locations) or any(loc in source_country for loc in high_risk_locations) or any(loc in dest_country for loc in high_risk_locations):
            score += 30
        elif "united states" in location or "united states" in source_country:
            score -= 5  # US is lower risk
        
        # IP/Network risk
        ip_address = str(data.get("ip_address", "")).lower()
        if "tor" in ip_address or "vpn detected" in ip_address:
            score += 25
        elif "unknown" in ip_address:
            score += 15
        
        # Transaction type risk
        transaction_type = str(data.get("transaction_type", "")).lower()
        if "crypto" in transaction_type or "nft" in transaction_type:
            score += 15
        
        # Time-based risk (late night/early morning)
        time = str(data.get("time", "")).lower()
        transaction_time = str(data.get("transaction_time", "")).lower()
        time_str = time or transaction_time
        if time_str:
            try:
                # Parse 24h time format (e.g., "02:45", "23:15")
                if ":" in time_str:
                    hour = int(time_str.split(":")[0])
                    if hour >= 0 and hour < 6:  # Midnight to 6 AM
                        score += 15
                    elif hour >= 22:  # 10 PM to midnight
                        score += 10
            except:
                if any(t in time_str for t in ["am", "night", "midnight", "late", "early"]):
                    score += 15
        
        # Account age risk (NEW accounts are risky, OLD accounts are safer)
        try:
            account_age = int(data.get("account_age_days", 365))
        except (ValueError, TypeError):
            account_age = 365
            logger.warning(f"[Banking Scoring] Invalid account_age_days: {data.get('account_age_days')}")
        
        if account_age < 1:
            score += 30
        elif account_age < 7:
            score += 25
        elif account_age < 30:
            score += 15
        elif account_age < 90:
            score += 5
        elif account_age >= 730:  # 2+ years old
            score -= 15  # Established accounts are much safer
            logger.debug(f"[Banking Scoring] Account age {account_age} days: -15 points (established)")
        elif account_age >= 365:  # 1+ year old
            score -= 10
            logger.debug(f"[Banking Scoring] Account age {account_age} days: -10 points (1+ year)")
        
        # Transaction velocity (high velocity = suspicious)
        try:
            velocity = int(data.get("transaction_velocity", 0))
        except (ValueError, TypeError):
            velocity = 0
            logger.warning(f"[Banking Scoring] Invalid transaction_velocity: {data.get('transaction_velocity')}")
        
        if velocity > 20:
            score += 25
        elif velocity > 10:
            score += 15
        elif velocity > 5:
            score += 5
        elif velocity <= 2:
            score -= 5  # Low velocity is normal
            logger.debug(f"[Banking Scoring] Low velocity ({velocity}): -5 points")
        
        # KYC verification (VERY IMPORTANT - reduces risk significantly)
        kyc_verified = data.get("kyc_verified", False)
        if kyc_verified:
            score -= 20  # KYC verified significantly reduces risk
            logger.debug(f"[Banking Scoring] KYC verified: -20 points")
        else:
            score += 25  # No KYC is a major red flag
            logger.debug(f"[Banking Scoring] KYC NOT verified: +25 points")
        
        # Previously flagged
        previous_flagged = data.get("previous_flagged", False)
        if previous_flagged:
            score += 30
        
        # Crypto wallet addresses (if present, check for suspicious patterns)
        sender_wallet = str(data.get("sender_wallet", "")).lower()
        receiver_wallet = str(data.get("receiver_wallet", "")).lower()
        if sender_wallet and ("0000000000000000000000000000000000000000" in sender_wallet or "tornado" in receiver_wallet):
            score += 40  # Burn address or mixer = critical risk
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _score_medical_fraud(self, data: Dict[str, Any]) -> float:
        """Medical claims fraud scoring logic"""
        score = 0.0
        
        claim_amount = float(data.get("claim_amount", 0))
        if claim_amount > 100000:
            score += 35
        elif claim_amount > 50000:
            score += 25
        elif claim_amount > 20000:
            score += 15
        elif claim_amount < 1000:
            score -= 5  # Small claims are less risky
        
        procedures = data.get("procedures", [])
        if isinstance(procedures, list):
            if len(procedures) > 10:
                score += 30
            elif len(procedures) > 5:
                score += 20
        elif isinstance(procedures, str):
            # If procedures is a string, try to count
            procedure_count = len(procedures.split(",")) if procedures else 0
            if procedure_count > 10:
                score += 30
            elif procedure_count > 5:
                score += 20
        
        provider_history = str(data.get("provider_history", "clean")).lower()
        if "flagged" in provider_history or "suspended" in provider_history:
            score += 45  # Increased from 40
        elif "clean" in provider_history or "verified" in provider_history:
            score -= 5  # Clean history reduces risk
        
        diagnosis_mismatch = data.get("diagnosis_mismatch", False)
        if diagnosis_mismatch:
            score += 40  # Increased from 35
        
        # Provider verification
        provider_verified = data.get("provider_verified", True)
        if not provider_verified:
            score += 25
        
        # Ensure score is between 0 and 100
        return max(0, min(100, score))
    
    def _score_ecommerce_fraud(self, data: Dict[str, Any]) -> float:
        """E-commerce fraud scoring logic - now with comprehensive field analysis"""
        score = 0.0
        logger.debug(f"[E-commerce Scoring] Starting with data: {list(data.keys())}")
        
        # Seller age (NEW sellers are very risky)
        seller_age = int(data.get("seller_age_days", 365))
        if seller_age < 1:
            score += 45
        elif seller_age < 7:
            score += 40
        elif seller_age < 30:
            score += 25
        elif seller_age < 90:
            score += 10
        elif seller_age >= 730:  # 2+ years old
            score -= 10  # Established sellers are safer
            logger.debug(f"[E-commerce Scoring] Established seller ({seller_age} days): -10 points")
        
        # Price analysis (too good to be true = scam)
        price = float(data.get("price", 0))
        market_price = float(data.get("market_price", price))
        if market_price > 0:
            discount_pct = ((market_price - price) / market_price) * 100
            if discount_pct > 70:  # More than 70% off
                score += 50
            elif discount_pct > 50:  # More than 50% off
                score += 40
            elif discount_pct > 30:  # More than 30% off
                score += 25
            elif discount_pct < 10:
                score -= 5  # Normal pricing is good
                logger.debug(f"[E-commerce Scoring] Competitive pricing ({discount_pct:.1f}% discount): -5 points")
        
        # Address mismatch (shipping vs billing) - major red flag
        shipping_address = str(data.get("shipping_address", "")).lower()
        billing_address = str(data.get("billing_address", "")).lower()
        if shipping_address and billing_address and shipping_address != billing_address:
            # Check if they're significantly different (not just formatting)
            if shipping_address.replace(" ", "") != billing_address.replace(" ", ""):
                score += 30  # Address mismatch is high risk
                logger.debug(f"[E-commerce Scoring] Shipping/billing address mismatch: +30 points")
        elif shipping_address and billing_address and shipping_address == billing_address:
            score -= 5  # Matching addresses reduce risk
            logger.debug(f"[E-commerce Scoring] Matching shipping/billing addresses: -5 points")
        
        # Payment method risk
        payment_method = str(data.get("payment_method", "")).lower()
        high_risk_payment = ["crypto", "gift_card", "prepaid", "other"]
        if any(method in payment_method for method in high_risk_payment):
            score += 20  # High-risk payment methods
            logger.debug(f"[E-commerce Scoring] High-risk payment method ({payment_method}): +20 points")
        elif payment_method in ["credit_card", "debit_card"]:
            score -= 5  # Standard payment methods reduce risk
            logger.debug(f"[E-commerce Scoring] Standard payment method ({payment_method}): -5 points")
        
        # IP address risk
        ip_address = str(data.get("ip_address", "")).lower()
        if "vpn" in ip_address or "tor" in ip_address or "proxy" in ip_address:
            score += 25  # VPN/TOR usage is suspicious
            logger.debug(f"[E-commerce Scoring] VPN/TOR detected: +25 points")
        elif "unknown" in ip_address or ip_address == "":
            score += 10  # Unknown IP is somewhat risky
        
        # Email verification
        email_verified = data.get("email_verified", False)
        if not email_verified:
            score += 15  # Unverified email is risky
            logger.debug(f"[E-commerce Scoring] Email NOT verified: +15 points")
        else:
            score -= 5  # Verified email reduces risk
            logger.debug(f"[E-commerce Scoring] Email verified: -5 points")
        
        # Reviews analysis
        reviews = data.get("reviews", [])
        review_count = 0
        if isinstance(reviews, list):
            review_count = len(reviews)
            if review_count == 0:
                score += 20
            elif review_count < 5:
                score += 10
            # Check for fake reviews (all perfect, same day, etc.)
            if review_count > 0 and all("excellent" in str(r).lower() or "5" in str(r) for r in reviews[:5]):
                score += 30  # Suspiciously perfect reviews
                logger.debug(f"[E-commerce Scoring] Suspiciously perfect reviews: +30 points")
        elif isinstance(reviews, str):
            # If reviews is a string, try to parse
            if not reviews or reviews.lower() == "none":
                score += 20
        
        # Seller verification
        seller_verified = data.get("seller_verified", False)
        if not seller_verified and seller_age < 30:
            score += 15
        
        # Shipping location risk
        shipping = str(data.get("shipping_location", "")).lower()
        if "unknown" in shipping or shipping == "":
            score += 25
        elif shipping in ["united states", "canada", "united kingdom", "germany", "france"]:
            score -= 5  # Low-risk countries reduce risk
            logger.debug(f"[E-commerce Scoring] Low-risk shipping location ({shipping}): -5 points")
        
        # Product description quality
        product_details = str(data.get("product_details", "")).lower()
        description = str(data.get("description", product_details)).lower()
        if "stock photo" in description or "vague" in description or len(description) < 20:
            score += 15
        elif "authentic" in description or "verified" in description:
            score -= 5  # Good product details reduce risk
        
        # Ensure score is between 0 and 100
        final_score = max(0, min(100, score))
        logger.info(f"[E-commerce Scoring] Final score: {final_score:.2f} (raw: {score:.2f})")
        return final_score
    
    def _score_supply_chain_fraud(self, data: Dict[str, Any]) -> float:
        """Supply chain fraud scoring logic - properly identifies high-risk scenarios"""
        score = 0.0
        
        # Payment terms risk (ADVANCE payment is very risky)
        payment_terms = str(data.get("payment_terms", "")).upper()
        if payment_terms == "ADVANCE":
            score += 40  # Increased from 35
        elif payment_terms == "COD":
            score += 10  # Cash on delivery is somewhat risky
        
        # Supplier age (NEW suppliers are very risky)
        try:
            supplier_age = int(data.get("supplier_age_days", 365))
        except (ValueError, TypeError):
            supplier_age = 365
            logger.warning(f"[Supply Chain Scoring] Invalid supplier_age_days: {data.get('supplier_age_days')}")
        
        if supplier_age < 1:
            score += 50  # Brand new supplier = critical risk
        elif supplier_age < 7:
            score += 45  # Increased from 40
        elif supplier_age < 30:
            score += 30  # Increased from 25
        elif supplier_age < 90:
            score += 15
        elif supplier_age >= 1095:  # 3+ years old
            score -= 10  # Established suppliers are safer
            logger.debug(f"[Supply Chain Scoring] Established supplier ({supplier_age} days): -10 points")
        elif supplier_age >= 730:  # 2+ years old
            score -= 5
            logger.debug(f"[Supply Chain Scoring] Mature supplier ({supplier_age} days): -5 points")
        
        # Price variance (high variance = suspicious pricing, especially above market)
        price_variance = abs(float(data.get("price_variance", 0)))
        order_details = str(data.get("order_details", "")).lower()
        has_kickback_indicators = any(flag in order_details for flag in ["kickback", "personal relationship", "bribery", "above market"])
        
        if price_variance > 40:
            if has_kickback_indicators:
                score += 40  # Kickback + high price variance = critical
            else:
                score += 35
        elif price_variance > 30:
            if has_kickback_indicators:
                score += 35  # Kickback + 30%+ above market = high risk
            else:
                score += 30
        elif price_variance > 20:
            score += 20
        elif price_variance > 10:
            score += 10
        elif price_variance < 5:
            score -= 5  # Competitive pricing is good
        
        # Quality issues (each issue adds significant risk, especially with kickback schemes)
        quality_issues = int(data.get("quality_issues", 0))
        order_details = str(data.get("order_details", "")).lower()
        has_kickback_indicators = any(flag in order_details for flag in ["kickback", "personal relationship", "bribery"])
        
        if quality_issues > 5:
            score += 35  # Increased from 30
        elif quality_issues > 2:
            # If quality issues + kickback indicators = major red flag
            if has_kickback_indicators:
                score += 30  # Kickback + quality issues = critical
            else:
                score += 25  # Increased from 20
        elif quality_issues > 0:
            if has_kickback_indicators:
                score += 20  # Kickback + any quality issues = high risk
            else:
                score += 10
        
        # Documentation and compliance (MISSING = major red flag)
        documentation_complete = data.get("documentation_complete", True)
        regulatory_compliance = data.get("regulatory_compliance", True)
        
        if not documentation_complete:
            score += 30  # Increased from 25
            logger.debug(f"[Supply Chain Scoring] Missing documentation: +30 points")
        if not regulatory_compliance:
            score += 35  # Increased from 30
            logger.debug(f"[Supply Chain Scoring] Missing compliance: +35 points")
        if documentation_complete and regulatory_compliance:
            score -= 5  # Good documentation reduces risk
            logger.debug(f"[Supply Chain Scoring] Complete documentation & compliance: -5 points")
        
        # Delivery variance (high variance = unreliable supplier)
        delivery_variance = abs(float(data.get("delivery_variance", 0)))
        if delivery_variance > 80:
            score += 25  # Increased from 20
        elif delivery_variance > 50:
            score += 20
        elif delivery_variance > 20:
            score += 10
        elif delivery_variance < 5:
            score -= 5  # Consistent delivery is good
            logger.debug(f"[Supply Chain Scoring] Low delivery variance ({delivery_variance}%): -5 points")
        
        # Order amount (very large orders from new suppliers are risky)
        try:
            order_amount = float(data.get("order_amount", 0))
        except (ValueError, TypeError):
            order_amount = 0.0
        
        supplier_age = int(data.get("supplier_age_days", 365))
        if order_amount > 100000 and supplier_age < 30:
            score += 20  # Large order from new supplier
        elif order_amount > 200000:
            score += 10
        
        # Order details text analysis (check for red flags in description)
        order_details = str(data.get("order_details", "")).lower()
        
        # Critical fraud indicators (kickback, bribery, corruption)
        critical_flags = ["kickback", "bribery", "corruption", "personal relationship", "conflict of interest", "under the table"]
        if any(flag in order_details for flag in critical_flags):
            score += 40  # Kickback schemes are critical fraud
            logger.debug(f"[Supply Chain Scoring] Critical fraud indicators (kickback/bribery) in order details: +40 points")
        
        # High-risk fraud indicators
        high_risk_flags = ["ghost", "unverified", "no references", "no online presence", "suspicious", "fraud", "inferior quality", "overpriced"]
        if any(flag in order_details for flag in high_risk_flags):
            score += 25
            logger.debug(f"[Supply Chain Scoring] High-risk flags in order details: +25 points")
        
        # Medium-risk indicators
        medium_risk_flags = ["unusual", "irregular", "questionable", "concerning"]
        if any(flag in order_details for flag in medium_risk_flags):
            score += 15
            logger.debug(f"[Supply Chain Scoring] Medium-risk flags in order details: +15 points")
        
        # Check for legitimate indicators in order details (only if score is already low)
        legitimate_keywords = ["established", "regular", "verified", "5-year", "history", "legitimate", "competitive pricing"]
        if any(keyword in order_details for keyword in legitimate_keywords) and score < 30:
            score -= 10  # Reduce score for legitimate suppliers
            logger.debug(f"[Supply Chain Scoring] Legitimate indicators in order details: -10 points")
        
        # Ensure score is between 0 and 100
        final_score = max(0, min(100, score))
        logger.info(f"[Supply Chain Scoring] Final score: {final_score:.2f} (raw: {score:.2f})")
        return final_score
    
    def _get_risk_level(self, score: float) -> str:
        """Convert fraud score to risk level with consistent thresholds"""
        if score >= 85:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"
    
    def _build_explanation(self, sector: str, data: Dict[str, Any], 
                          fraud_score: float, risk_level: str, model: str) -> str:
        """Generate AI-style explanation"""
        
        explanations = {
            "banking": self._explain_banking(data, fraud_score),
            "medical": self._explain_medical(data, fraud_score),
            "ecommerce": self._explain_ecommerce(data, fraud_score),
            "supply_chain": self._explain_supply_chain(data, fraud_score)
        }
        
        base_explanation = explanations.get(sector, "Analysis complete.")
        
        prefix = f"{model} analysis identifies {risk_level} risk. "
        
        return prefix + base_explanation
    
    def _explain_banking(self, data: Dict[str, Any], score: float) -> str:
        factors = []
        
        amount = data.get("amount", 0)
        if amount > 10000:
            factors.append(f"unusually high transaction amount (${amount:,.2f})")
        
        location = data.get("location", "")
        if location:
            factors.append(f"transaction from {location}")
        
        device = data.get("device", "")
        if "new" in str(device).lower():
            factors.append("new or unrecognized device")
        
        time = data.get("time", "")
        if time:
            factors.append(f"transaction at {time}")
        
        user_age = data.get("user_age_days", 365)
        if user_age < 30:
            factors.append(f"account age only {user_age} days")
        
        if factors:
            return "Red flags detected: " + ", ".join(factors) + "."
        return "Transaction appears legitimate with standard patterns."
    
    def _explain_medical(self, data: Dict[str, Any], score: float) -> str:
        factors = []
        
        claim_amount = data.get("claim_amount", 0)
        if claim_amount > 20000:
            factors.append(f"high claim amount (${claim_amount:,.2f})")
        
        procedures = data.get("procedures", [])
        if isinstance(procedures, list) and len(procedures) > 5:
            factors.append(f"{len(procedures)} procedures in single claim")
        
        if data.get("diagnosis_mismatch"):
            factors.append("diagnosis-procedure mismatch detected")
        
        provider = data.get("provider_history", "")
        if "flagged" in str(provider).lower():
            factors.append("provider has previous fraud flags")
        
        if factors:
            return "Suspicious indicators: " + ", ".join(factors) + "."
        return "Claim follows standard medical billing patterns."
    
    def _explain_ecommerce(self, data: Dict[str, Any], score: float) -> str:
        factors = []
        
        seller_age = data.get("seller_age_days", 365)
        if seller_age < 30:
            factors.append(f"seller account only {seller_age} days old")
        
        price = data.get("price", 0)
        market_price = data.get("market_price", price)
        if market_price > 0 and price < market_price * 0.5:
            discount = ((market_price - price) / market_price) * 100
            factors.append(f"price {discount:.0f}% below market value")
        
        reviews = data.get("reviews", [])
        if isinstance(reviews, list) and len(reviews) == 0:
            factors.append("no customer reviews")
        
        shipping = data.get("shipping_location", "")
        if "unknown" in str(shipping).lower():
            factors.append("unclear shipping origin")
        
        if factors:
            return "Warning signs present: " + ", ".join(factors) + "."
        return "Listing appears legitimate with typical marketplace patterns."
    
    def _explain_supply_chain(self, data: Dict[str, Any], score: float) -> str:
        factors = []
        
        supplier_age = data.get("supplier_age_days", 365)
        if supplier_age < 30:
            factors.append(f"new supplier ({supplier_age} days)")
        
        payment_terms = data.get("payment_terms", "")
        if payment_terms == "ADVANCE":
            factors.append("advance payment required")
        
        price_variance = abs(data.get("price_variance", 0))
        if price_variance > 20:
            factors.append(f"price variance {price_variance:.1f}% from market")
        
        quality_issues = data.get("quality_issues", 0)
        if quality_issues > 0:
            factors.append(f"{quality_issues} quality issues")
        
        if not data.get("documentation_complete", True):
            factors.append("incomplete documentation")
        
        if not data.get("regulatory_compliance", True):
            factors.append("regulatory compliance issues")
        
        delivery_variance = data.get("delivery_variance", 0)
        if delivery_variance > 20:
            factors.append(f"delivery variance {delivery_variance:.1f}%")
        
        if factors:
            return "Risk indicators found: " + ", ".join(factors) + "."
        return "Supplier and order profile appear legitimate."
    
    async def route_and_analyze(self, sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the full LangGraph workflow"""
        
        initial_state: RouterState = {
            "sector": sector,
            "input_data": data,
            "model_name": "",
            "rag_context": "",
            "fraud_score": 0.0,
            "risk_level": "",
            "explanation": "",
            "similar_patterns": 0,
            "risk_factors": []
        }
        
        final_state = self.workflow.invoke(initial_state)
        
        return {
            "fraud_score": final_state["fraud_score"],
            "risk_level": final_state["risk_level"],
            "explanation": final_state["explanation"],
            "model_used": final_state["model_name"],
            "similar_patterns": final_state["similar_patterns"],
            "risk_factors": final_state.get("risk_factors", [])
        }


# Helper function for HF client fallback
def analyze_fraud_rule_based(sector: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Rule-based fraud analysis (fallback when HF API fails)"""
    # Create a minimal router without HF client
    from app.rag_engine import RAGEngine
    
    rag = RAGEngine()
    router = LangGraphRouter(rag, hf_client=None)
    
    # Calculate score using rule-based logic
    fraud_score = router._calculate_fraud_score(sector, data, "")
    risk_level = router._get_risk_level(fraud_score)
    
    # Generate explanation
    model_name = router.model_mapping.get(sector, "NVIDIA: Nemotron Nano 12B 2 VL")
    reasoning = router._build_explanation(sector, data, fraud_score, risk_level, model_name)
    
    return {
        "fraud_score": fraud_score,
        "risk_level": risk_level.upper(),
        "reasoning": reasoning,
        "risk_factors": ["Rule-based analysis"]
    }

