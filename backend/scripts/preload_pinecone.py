"""
Preload fraud patterns into Pinecone vector database.

This script loads comprehensive fraud patterns for all sectors into Pinecone.
Run this once to populate the index with fraud detection patterns.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag_engine import RAGEngine
from app.utils.mcp_pinecone import MCPPinecone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_comprehensive_patterns():
    """Get comprehensive fraud patterns for all sectors"""
    
    patterns = {
        "banking": [
            # Critical Risk Patterns
            {
                "description": "Crypto mixer laundering with TOR network and burn address transactions",
                "risk_level": "critical",
                "indicators": ["crypto mixer", "tor network", "burn address", "laundering", "sanctioned wallet"]
            },
            {
                "description": "Wire transfer to known money laundering destination from high-risk country",
                "risk_level": "critical",
                "indicators": ["wire transfer", "high-risk country", "sanctions list", "money laundering"]
            },
            {
                "description": "Crypto rug pull with new account high-velocity transactions to suspicious wallets",
                "risk_level": "critical",
                "indicators": ["crypto rug pull", "new account", "high velocity", "suspicious wallet", "scam"]
            },
            # High Risk Patterns
            {
                "description": "Large transaction from high-risk country using new device at unusual time",
                "risk_level": "high",
                "indicators": ["amount > 10000", "high-risk location", "new device", "unusual time"]
            },
            {
                "description": "Multiple small transactions to different accounts within short timeframe indicating structuring",
                "risk_level": "high",
                "indicators": ["structuring", "rapid succession", "multiple recipients", "threshold avoidance"]
            },
            {
                "description": "Account created recently with immediate large withdrawal attempt and no KYC",
                "risk_level": "high",
                "indicators": ["new account", "large amount", "immediate activity", "no kyc"]
            },
            {
                "description": "Rapid account verification followed by large transfer to unknown destination",
                "risk_level": "high",
                "indicators": ["fast verification", "large transfer", "suspicious timing", "unknown destination"]
            },
            {
                "description": "Transaction amount just below reporting threshold multiple times",
                "risk_level": "high",
                "indicators": ["threshold avoidance", "structuring", "pattern", "suspicious behavior"]
            },
            {
                "description": "NFT wash trading with coordinated transactions and fake volume",
                "risk_level": "high",
                "indicators": ["nft wash trading", "coordinated", "fake volume", "market manipulation"]
            },
            # Medium Risk Patterns
            {
                "description": "Transaction from VPN or proxy with mismatched billing address",
                "risk_level": "medium",
                "indicators": ["vpn usage", "address mismatch", "anonymous", "proxy"]
            },
            {
                "description": "Cryptocurrency purchase with new payment method from abroad",
                "risk_level": "medium",
                "indicators": ["crypto", "new payment", "international", "moderate risk"]
            },
            {
                "description": "Money laundering pattern with moderate transaction velocity from medium-risk location",
                "risk_level": "medium",
                "indicators": ["money laundering", "moderate velocity", "medium-risk location", "suspicious pattern"]
            },
            # Low Risk Patterns (Legitimate)
            {
                "description": "Standard transaction from known location during business hours with KYC verified account",
                "risk_level": "low",
                "indicators": ["established account", "normal pattern", "verified location", "kyc verified", "legitimate"]
            },
            {
                "description": "Recurring payment to verified merchant with consistent amount and established history",
                "risk_level": "low",
                "indicators": ["recurring", "verified merchant", "consistent", "established", "legitimate"]
            },
            {
                "description": "Normal business transaction between legitimate countries with verified accounts",
                "risk_level": "low",
                "indicators": ["normal business", "legitimate countries", "verified accounts", "standard transaction"]
            },
            {
                "description": "Legitimate wire transfer with KYC verified account and established transaction history",
                "risk_level": "low",
                "indicators": ["legitimate wire", "kyc verified", "established history", "normal business hours", "verified"]
            }
        ],
        "medical": [
            {
                "description": "High-value claim with multiple unnecessary procedures from flagged provider",
                "risk_level": "high",
                "indicators": ["high amount", "excessive procedures", "provider history"]
            },
            {
                "description": "Billing code mismatch with documented diagnosis",
                "risk_level": "high",
                "indicators": ["code mismatch", "documentation inconsistency"]
            },
            {
                "description": "Duplicate claims submitted for same patient and date",
                "risk_level": "high",
                "indicators": ["duplicate", "same date", "double billing"]
            },
            {
                "description": "Unbundling of procedures to inflate claim value",
                "risk_level": "medium",
                "indicators": ["unbundling", "procedure splitting", "inflation"]
            },
            {
                "description": "Claim for service not typically performed by provider specialty",
                "risk_level": "medium",
                "indicators": ["specialty mismatch", "unusual procedure"]
            },
            {
                "description": "Upcoding from basic to complex procedure without justification",
                "risk_level": "high",
                "indicators": ["upcoding", "no justification", "complex procedure"]
            },
            {
                "description": "Claims for services on dates when patient was hospitalized elsewhere",
                "risk_level": "critical",
                "indicators": ["date conflict", "hospitalization", "impossible service"]
            },
            {
                "description": "Provider billing for services at frequency exceeding medical necessity",
                "risk_level": "high",
                "indicators": ["excessive frequency", "medical necessity", "overutilization"]
            },
            {
                "description": "Routine claim matching typical care patterns",
                "risk_level": "low",
                "indicators": ["routine care", "appropriate codes", "clean provider"]
            },
            {
                "description": "Standard preventive care claim with proper documentation",
                "risk_level": "low",
                "indicators": ["preventive", "documented", "appropriate"]
            }
        ],
        "ecommerce": [
            # Critical Risk Patterns
            {
                "description": "Counterfeit product listing using brand images without authorization with unverified seller",
                "risk_level": "critical",
                "indicators": ["counterfeit", "brand violation", "unauthorized", "unverified seller", "stock photos"]
            },
            {
                "description": "Order with shipping and billing address mismatch using VPN IP and unverified email",
                "risk_level": "critical",
                "indicators": ["address mismatch", "vpn", "unverified email", "high risk payment", "suspicious"]
            },
            {
                "description": "New seller offering luxury items 70% below market price with crypto payment and fake reviews",
                "risk_level": "critical",
                "indicators": ["new seller", "below market", "luxury goods", "crypto payment", "fake reviews", "unverified"]
            },
            # High Risk Patterns
            {
                "description": "New seller offering luxury items far below market price with no reviews and unverified email",
                "risk_level": "high",
                "indicators": ["new seller", "below market", "luxury goods", "no reviews", "unverified email"]
            },
            {
                "description": "Order with shipping address different from billing address using gift card payment",
                "risk_level": "high",
                "indicators": ["address mismatch", "gift card", "payment method", "shipping billing different"]
            },
            {
                "description": "Seller with fake reviews pattern and suspicious shipping location with VPN IP address",
                "risk_level": "high",
                "indicators": ["fake reviews", "suspicious location", "review pattern", "vpn", "ip address"]
            },
            {
                "description": "Product listing with suspiciously perfect reviews all from same day and unverified seller",
                "risk_level": "high",
                "indicators": ["review manipulation", "same day", "perfect scores", "unverified", "suspicious"]
            },
            {
                "description": "Seller with history of non-delivery complaints and chargebacks using high-risk payment methods",
                "risk_level": "high",
                "indicators": ["non-delivery", "chargebacks", "complaints", "payment method", "high risk"]
            },
            {
                "description": "Order with unverified email and VPN IP address from unknown shipping location",
                "risk_level": "high",
                "indicators": ["unverified email", "vpn", "ip address", "unknown location", "suspicious"]
            },
            # Medium Risk Patterns
            {
                "description": "Listing with stock photos and vague product descriptions from new seller",
                "risk_level": "medium",
                "indicators": ["stock photos", "vague description", "no verification", "new seller"]
            },
            {
                "description": "Multiple identical listings from different sellers at same price with similar patterns",
                "risk_level": "medium",
                "indicators": ["duplicate listings", "coordinated", "same price", "pattern"]
            },
            {
                "description": "New account making high-value purchase with expedited shipping and unverified email",
                "risk_level": "medium",
                "indicators": ["new buyer", "high value", "expedited", "unverified email"]
            },
            {
                "description": "Order with moderate price discount and standard payment method from verified seller",
                "risk_level": "medium",
                "indicators": ["moderate discount", "standard payment", "verified seller", "acceptable risk"]
            },
            # Low Risk Patterns (Legitimate)
            {
                "description": "Established seller with verified reviews and matching shipping billing addresses",
                "risk_level": "low",
                "indicators": ["established", "verified", "good history", "matching addresses", "legitimate"]
            },
            {
                "description": "Product with authentic reviews and verified seller credentials using standard payment",
                "risk_level": "low",
                "indicators": ["authentic reviews", "verified", "legitimate", "standard payment", "email verified"]
            },
            {
                "description": "Order with verified email and standard payment method from established seller",
                "risk_level": "low",
                "indicators": ["email verified", "standard payment", "established seller", "legitimate", "low risk"]
            },
            {
                "description": "Legitimate order with matching addresses and verified payment from trusted seller",
                "risk_level": "low",
                "indicators": ["matching addresses", "verified payment", "trusted seller", "legitimate", "normal"]
            }
        ],
        "supply_chain": [
            # Critical Risk Patterns
            {
                "description": "Ghost supplier with no verifiable business registration requesting advance payment",
                "risk_level": "critical",
                "indicators": ["ghost supplier", "no registration", "unverifiable", "advance payment"]
            },
            {
                "description": "Kickback scheme with purchasing manager personal relationship and inflated prices",
                "risk_level": "critical",
                "indicators": ["kickback", "personal relationship", "price inflation", "bribery", "corruption"]
            },
            {
                "description": "Supplier with no online presence requesting large advance payment for unverified address",
                "risk_level": "critical",
                "indicators": ["no online presence", "advance payment", "unverified address", "large amount"]
            },
            # High Risk Patterns
            {
                "description": "New supplier less than 7 days old requesting advance payment with missing documentation",
                "risk_level": "high",
                "indicators": ["new supplier", "advance payment", "missing documentation", "supplier age"]
            },
            {
                "description": "Supplier with prices 35% above market rate and quality issues indicating kickback scheme",
                "risk_level": "high",
                "indicators": ["price inflation", "above market", "quality issues", "kickback", "inferior products"]
            },
            {
                "description": "Multiple missing documents with unexplained gaps in audit trail",
                "risk_level": "high",
                "indicators": ["missing documents", "timeline gaps", "incomplete", "audit trail"]
            },
            {
                "description": "Supplier with history of quality violations and delivery delays requesting advance payment",
                "risk_level": "high",
                "indicators": ["quality issues", "delays", "violations", "advance payment", "poor track record"]
            },
            {
                "description": "Purchase order amount significantly higher than market rate from new supplier",
                "risk_level": "high",
                "indicators": ["price inflation", "market rate", "overpayment", "new supplier"]
            },
            {
                "description": "Invoice padding with duplicate charges and inflated shipping costs",
                "risk_level": "high",
                "indicators": ["invoice padding", "duplicate charges", "inflated costs", "ambiguous line items"]
            },
            # Medium Risk Patterns
            {
                "description": "Inconsistent data across related records with minor documentation gaps",
                "risk_level": "medium",
                "indicators": ["data inconsistency", "record mismatch", "documentation gaps"]
            },
            {
                "description": "Delayed documentation entries with backdating but proper authorization",
                "risk_level": "medium",
                "indicators": ["backdating", "delayed entry", "timestamp issues", "authorized"]
            },
            {
                "description": "Supplier with moderate price variance and acceptable quality record",
                "risk_level": "medium",
                "indicators": ["price variance", "moderate risk", "acceptable quality"]
            },
            # Low Risk Patterns (Legitimate)
            {
                "description": "Established supplier with 5-year history and complete documentation requesting standard payment terms",
                "risk_level": "low",
                "indicators": ["established", "5-year history", "complete documentation", "standard terms", "legitimate"]
            },
            {
                "description": "Verified supplier with consistent delivery and quality records using standard payment terms",
                "risk_level": "low",
                "indicators": ["verified", "consistent", "quality records", "standard terms", "reliable"]
            },
            {
                "description": "Complete documentation with proper authorization chain and competitive pricing",
                "risk_level": "low",
                "indicators": ["complete", "authorized", "proper workflow", "competitive pricing", "transparent"]
            },
            {
                "description": "Regular component order from established supplier with competitive pricing and full documentation",
                "risk_level": "low",
                "indicators": ["regular order", "established supplier", "competitive pricing", "full documentation", "legitimate"]
            },
            {
                "description": "Seasonal high-volume order from verified supplier with consistent delivery history",
                "risk_level": "low",
                "indicators": ["seasonal order", "verified supplier", "consistent delivery", "established relationship"]
            }
        ]
    }
    
    return patterns


def get_mcp_context_data():
    """Get external context data for MCP namespace"""
    
    # Sample blockchain wallet addresses and transaction data
    blockchain_data = [
        {"context_type": "wallet", "key": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "risk_score": 0.1, "transaction_count": 150, "first_seen": "2024-01-15"},
        {"context_type": "wallet", "key": "0x0000000000000000000000000000000000000000", "address": "0x0000000000000000000000000000000000000000", "risk_score": 0.8, "transaction_count": 5, "first_seen": "2024-11-01"},
        {"context_type": "wallet", "key": "0x8ba1f109551bD432803012645Hac136c22C1779", "address": "0x8ba1f109551bD432803012645Hac136c22C1779", "risk_score": 0.2, "transaction_count": 89, "first_seen": "2023-06-20"},
        {"context_type": "wallet", "key": "0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2", "address": "0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2", "risk_score": 0.3, "transaction_count": 234, "first_seen": "2023-03-10"},
        {"context_type": "wallet", "key": "0x4B20993Bc481177ec7E8f571ceCaE8A9e22C02db", "address": "0x4B20993Bc481177ec7E8f571ceCaE8A9e22C02db", "risk_score": 0.15, "transaction_count": 567, "first_seen": "2022-11-05"},
    ]
    
    # Sample transaction history
    transaction_data = [
        # Legitimate transactions
        {"context_type": "transaction", "key": "tx_abc123def456", "transaction_id": "tx_abc123def456", "amount": 1000, "date": "2024-11-15", "type": "transfer", "risk_indicators": [], "status": "completed", "verified": True},
        {"context_type": "transaction", "key": "tx_xyz789ghi012", "transaction_id": "tx_xyz789ghi012", "amount": 500, "date": "2024-11-10", "type": "deposit", "risk_indicators": [], "status": "completed", "verified": True},
        {"context_type": "transaction", "key": "tx_legitimate_business", "transaction_id": "tx_legitimate_business", "amount": 12500, "date": "2024-11-18", "type": "wire_transfer", "risk_indicators": [], "status": "completed", "verified": True, "kyc_verified": True},
        # Suspicious transactions
        {"context_type": "transaction", "key": "tx_suspicious001", "transaction_id": "tx_suspicious001", "amount": 50000, "date": "2024-11-20", "type": "withdrawal", "risk_indicators": ["large_amount", "new_account"], "status": "pending", "verified": False},
        {"context_type": "transaction", "key": "tx_crypto_mixer", "transaction_id": "tx_crypto_mixer", "amount": 2500000, "date": "2024-11-19", "type": "crypto_transfer", "risk_indicators": ["mixer", "sanctioned", "high_value"], "status": "completed", "verified": False, "sender_wallet": "0xTornadoCash1234567890abcdef123456789abc"},
    ]
    
    # Sample healthcare provider data
    provider_data = [
        {"context_type": "provider", "key": "PROV_001", "provider_id": "PROV_001", "license_status": "active", "specialty": "Cardiology", "years_practicing": 15, "complaints": 0, "verified": True},
        {"context_type": "provider", "key": "PROV_002", "provider_id": "PROV_002", "license_status": "active", "specialty": "Orthopedics", "years_practicing": 8, "complaints": 2, "verified": True},
        {"context_type": "provider", "key": "PROV_003", "provider_id": "PROV_003", "license_status": "suspended", "specialty": "General Practice", "years_practicing": 20, "complaints": 15, "verified": False},
        {"context_type": "provider", "key": "PROV_004", "provider_id": "PROV_004", "license_status": "active", "specialty": "Dermatology", "years_practicing": 12, "complaints": 1, "verified": True},
        {"context_type": "provider", "key": "PROV_005", "provider_id": "PROV_005", "license_status": "active", "specialty": "Pediatrics", "years_practicing": 6, "complaints": 0, "verified": True},
    ]
    
    # Sample e-commerce seller data
    seller_data = [
        # Legitimate sellers
        {"context_type": "seller", "key": "seller_trusted_001", "seller_id": "seller_trusted_001", "rating": 4.8, "total_reviews": 1250, "account_age_days": 1095, "verified": True, "suspicious_activity": False, "email_verified": True, "payment_methods": ["credit_card", "paypal"], "shipping_countries": ["United States", "Canada"]},
        {"context_type": "seller", "key": "seller_established_004", "seller_id": "seller_established_004", "rating": 4.5, "total_reviews": 890, "account_age_days": 730, "verified": True, "suspicious_activity": False, "email_verified": True, "payment_methods": ["credit_card", "debit_card"], "shipping_countries": ["United States", "United Kingdom"]},
        {"context_type": "seller", "key": "seller_premium_005", "seller_id": "seller_premium_005", "rating": 4.9, "total_reviews": 2100, "account_age_days": 1825, "verified": True, "suspicious_activity": False, "email_verified": True, "payment_methods": ["credit_card", "paypal", "bank_transfer"], "shipping_countries": ["United States", "Canada", "United Kingdom"]},
        # Suspicious sellers
        {"context_type": "seller", "key": "seller_new_002", "seller_id": "seller_new_002", "rating": 5.0, "total_reviews": 3, "account_age_days": 5, "verified": False, "suspicious_activity": True, "email_verified": False, "payment_methods": ["crypto", "gift_card"], "shipping_countries": ["Unknown"]},
        {"context_type": "seller", "key": "seller_suspicious_003", "seller_id": "seller_suspicious_003", "rating": 2.1, "total_reviews": 45, "account_age_days": 30, "verified": False, "suspicious_activity": True, "email_verified": False, "payment_methods": ["crypto", "other"], "shipping_countries": ["Unknown", "Overseas"]},
        {"context_type": "seller", "key": "seller_fraud_006", "seller_id": "seller_fraud_006", "rating": 1.2, "total_reviews": 8, "account_age_days": 2, "verified": False, "suspicious_activity": True, "email_verified": False, "payment_methods": ["crypto"], "shipping_countries": ["Unknown"], "chargebacks": 5, "non_delivery_complaints": 3},
    ]
    
    # Sample e-commerce order data
    order_data = [
        # Legitimate orders
        {"context_type": "order", "key": "order_legit_001", "order_id": "ORD-2024-12345", "amount": 299.99, "shipping_address": "123 Main St, New York, NY, United States", "billing_address": "123 Main St, New York, NY, United States", "payment_method": "credit_card", "email_verified": True, "ip_address": "192.168.1.100", "seller_verified": True},
        {"context_type": "order", "key": "order_legit_002", "order_id": "ORD-2024-67890", "amount": 1250.00, "shipping_address": "456 Oak Ave, Los Angeles, CA, United States", "billing_address": "456 Oak Ave, Los Angeles, CA, United States", "payment_method": "paypal", "email_verified": True, "ip_address": "203.45.67.89", "seller_verified": True},
        # Suspicious orders
        {"context_type": "order", "key": "order_suspicious_001", "order_id": "ORD-2024-99999", "amount": 5000.00, "shipping_address": "789 Unknown St, Unknown City, Unknown Country", "billing_address": "123 Different Ave, Different City, Different Country", "payment_method": "crypto", "email_verified": False, "ip_address": "VPN Detected", "seller_verified": False},
        {"context_type": "order", "key": "order_fraud_002", "order_id": "ORD-2024-88888", "amount": 15000.00, "shipping_address": "Unknown location", "billing_address": "Different unknown location", "payment_method": "gift_card", "email_verified": False, "ip_address": "TOR Network", "seller_verified": False, "address_mismatch": True},
    ]
    
    return {
        "blockchain": blockchain_data,
        "transaction": transaction_data,
        "provider": provider_data,
        "seller": seller_data,
        "order": order_data
    }


def main():
    """Main function to preload patterns into Pinecone"""
    
    logger.info("🚀 [Pinecone] Starting data preload for both namespaces...")
    logger.info("=" * 70)
    
    # Check environment variables
    if not os.getenv("PINECONE_API_KEY"):
        logger.error("❌ [Pinecone] PINECONE_API_KEY environment variable not set")
        sys.exit(1)
    
    logger.info(f"✅ [Pinecone] API key found")
    logger.info(f"📦 [Pinecone] Index name: {os.getenv('PINECONE_INDEX_NAME', 'fraudforge-master')}")
    logger.info("")
    
    # ============================================================
    # STEP 1: Load RAG namespace
    # ============================================================
    logger.info("📋 STEP 1: Loading 'rag' namespace with fraud patterns")
    logger.info("-" * 70)
    
    # Initialize RAG engine with 'rag' namespace
    try:
        logger.info(f"🔧 [Pinecone] Initializing RAG engine for namespace: 'rag'")
        rag_engine = RAGEngine(namespace="rag")
        rag_engine.initialize()
        logger.info(f"✅ [Pinecone] RAG engine ready for namespace 'rag'")
    except Exception as e:
        logger.error(f"❌ [Pinecone] Failed to initialize RAG engine: {e}")
        sys.exit(1)
    
    # Get comprehensive patterns
    all_patterns = get_comprehensive_patterns()
    
    # Upsert patterns for each sector
    total_patterns = 0
    for sector, patterns in all_patterns.items():
        logger.info(f"")
        logger.info(f"📦 [Pinecone] Loading {len(patterns)} patterns for sector: '{sector}'")
        logger.info(f"   → Target namespace: 'rag'")
        try:
            rag_engine.upsert_patterns(patterns, sector)
            total_patterns += len(patterns)
            logger.info(f"✅ [Pinecone] Sector '{sector}' loaded successfully")
        except Exception as e:
            logger.error(f"❌ [Pinecone] Failed to load patterns for {sector}: {e}")
            continue
    
    # Verify RAG namespace
    logger.info("")
    logger.info("📊 [Pinecone] Verifying 'rag' namespace...")
    rag_count = rag_engine.get_collection_count()
    logger.info(f"✅ [Pinecone] RAG namespace preload complete!")
    logger.info(f"   📦 Namespace: 'rag'")
    logger.info(f"   📈 Vectors loaded: {rag_count}")
    logger.info(f"   📊 Expected: {total_patterns} patterns")
    
    if rag_count >= total_patterns:
        logger.info(f"✅ [Pinecone] All {total_patterns} RAG patterns successfully loaded into namespace 'rag'!")
    else:
        logger.warning(f"⚠️  [Pinecone] Expected {total_patterns} patterns but found {rag_count} in 'rag' namespace")
    
    # ============================================================
    # STEP 2: Load MCP namespace
    # ============================================================
    logger.info("")
    logger.info("=" * 70)
    logger.info("📋 STEP 2: Loading 'mcp' namespace with external context data")
    logger.info("-" * 70)
    
    try:
        logger.info(f"🔧 [Pinecone] Initializing MCP client for namespace: 'mcp'")
        mcp_pinecone = MCPPinecone()
        mcp_pinecone.initialize()
        
        if not mcp_pinecone.initialized:
            logger.warning("⚠️  [Pinecone] MCP Pinecone not initialized, skipping MCP namespace preload")
            logger.info("✅ [Pinecone] RAG namespace loaded successfully")
            return
        
        logger.info(f"✅ [Pinecone] MCP client ready for namespace 'mcp'")
        
        mcp_data = get_mcp_context_data()
        total_mcp_items = 0
        
        # Store blockchain data
        logger.info(f"")
        logger.info(f"📦 [Pinecone] Loading {len(mcp_data['blockchain'])} blockchain wallet records to namespace 'mcp'...")
        for item in mcp_data['blockchain']:
            logger.debug(f"   → Storing wallet: {item['key']}")
            mcp_pinecone.store_context(
                context_type=item['context_type'],
                key=item['key'],
                data=item
            )
            total_mcp_items += 1
        logger.info(f"✅ [Pinecone] Blockchain data loaded: {len(mcp_data['blockchain'])} records")
        
        # Store transaction data
        logger.info(f"")
        logger.info(f"📦 [Pinecone] Loading {len(mcp_data['transaction'])} transaction records to namespace 'mcp'...")
        for item in mcp_data['transaction']:
            logger.debug(f"   → Storing transaction: {item['key']}")
            mcp_pinecone.store_context(
                context_type=item['context_type'],
                key=item['key'],
                data=item
            )
            total_mcp_items += 1
        logger.info(f"✅ [Pinecone] Transaction data loaded: {len(mcp_data['transaction'])} records")
        
        # Store provider data
        logger.info(f"")
        logger.info(f"📦 [Pinecone] Loading {len(mcp_data['provider'])} healthcare provider records to namespace 'mcp'...")
        for item in mcp_data['provider']:
            logger.debug(f"   → Storing provider: {item['key']}")
            mcp_pinecone.store_context(
                context_type=item['context_type'],
                key=item['key'],
                data=item
            )
            total_mcp_items += 1
        logger.info(f"✅ [Pinecone] Provider data loaded: {len(mcp_data['provider'])} records")
        
        # Store seller data
        logger.info(f"")
        logger.info(f"📦 [Pinecone] Loading {len(mcp_data['seller'])} e-commerce seller records to namespace 'mcp'...")
        for item in mcp_data['seller']:
            logger.debug(f"   → Storing seller: {item['key']}")
            mcp_pinecone.store_context(
                context_type=item['context_type'],
                key=item['key'],
                data=item
            )
            total_mcp_items += 1
        logger.info(f"✅ [Pinecone] Seller data loaded: {len(mcp_data['seller'])} records")
        
        # Store order data (new - for e-commerce fraud detection)
        if 'order' in mcp_data:
            logger.info(f"")
            logger.info(f"📦 [Pinecone] Loading {len(mcp_data['order'])} e-commerce order records to namespace 'mcp'...")
            for item in mcp_data['order']:
                logger.debug(f"   → Storing order: {item['key']}")
                mcp_pinecone.store_context(
                    context_type=item['context_type'],
                    key=item['key'],
                    data=item
                )
                total_mcp_items += 1
            logger.info(f"✅ [Pinecone] Order data loaded: {len(mcp_data['order'])} records")
        
        logger.info("")
        logger.info("📊 [Pinecone] Verifying 'mcp' namespace...")
        logger.info(f"✅ [Pinecone] MCP namespace preload complete!")
        logger.info(f"   📦 Namespace: 'mcp'")
        logger.info(f"   📈 Context items loaded: {total_mcp_items}")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎉 [Pinecone] ALL NAMESPACES PRELOADED SUCCESSFULLY!")
        logger.info("=" * 70)
        logger.info(f"   ✅ 'rag' namespace: {rag_count} fraud patterns")
        logger.info(f"   ✅ 'mcp' namespace: {total_mcp_items} context items")
        logger.info(f"   📊 Total vectors: {rag_count + total_mcp_items}")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ [Pinecone] Failed to preload MCP namespace: {e}", exc_info=True)
        logger.warning("⚠️  [Pinecone] RAG namespace loaded successfully, but MCP namespace failed")
        logger.info(f"✅ [Pinecone] RAG namespace complete: {rag_count} patterns in 'rag' namespace")


if __name__ == "__main__":
    main()



