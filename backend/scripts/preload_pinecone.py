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

from app.core.rag_engine import RAGEngine

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
                "description": "Wire transfer to OFAC sanctioned country or high-risk fraud country (Nigeria, Iran, Russia, etc.)",
                "risk_level": "critical",
                "indicators": ["wire transfer", "ofac sanctioned", "high-risk country", "nigeria", "iran", "russia", "cuba", "north korea", "syria", "sanctions list", "money laundering"]
            },
            {
                "description": "Transaction involving OFAC sanctioned country with VPN and unverified KYC",
                "risk_level": "critical",
                "indicators": ["ofac country", "sanctioned country", "vpn", "unverified kyc", "high-risk location", "nigeria", "ghana", "pakistan", "bangladesh"]
            },
            {
                "description": "Crypto rug pull with new account high-velocity transactions to suspicious wallets",
                "risk_level": "critical",
                "indicators": ["crypto rug pull", "new account", "high velocity", "suspicious wallet", "scam"]
            },
            # High Risk Patterns
            {
                "description": "Large transaction from OFAC sanctioned or high-risk fraud country using new device at unusual time",
                "risk_level": "high",
                "indicators": ["amount > 10000", "ofac country", "high-risk location", "nigeria", "ghana", "pakistan", "russia", "new device", "unusual time"]
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
                "description": "Money laundering pattern with moderate transaction velocity from OFAC sanctioned or medium-risk location",
                "risk_level": "medium",
                "indicators": ["money laundering", "moderate velocity", "ofac country", "medium-risk location", "suspicious pattern"]
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
                "description": "High-value claim with multiple unnecessary procedures from provider in OFAC sanctioned country",
                "risk_level": "high",
                "indicators": ["high amount", "excessive procedures", "provider history", "ofac country", "sanctioned country"]
            },
            {
                "description": "Medical claim from OFAC sanctioned or high-risk fraud country with suspicious billing patterns",
                "risk_level": "critical",
                "indicators": ["ofac country", "sanctioned country", "high-risk location", "suspicious billing", "upcoding", "unbundling"]
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
                "description": "Unbundling: total knee arthroplasty CPT 27447 billed with arthroscopy 29881/29882 and revision 27486 in the same operative session when components are typically bundled",
                "risk_level": "medium",
                "indicators": ["unbundling", "27447", "29881", "29882", "27486", "same operative session", "typically bundled", "procedure splitting"]
            },
            {
                "description": "Claim for service not typically performed by provider specialty",
                "risk_level": "medium",
                "indicators": ["specialty mismatch", "unusual procedure"]
            },
            {
                "description": "Upcoding: same-day cardiology battery ECG stress echo chest x-ray labs without intensity justified by clinical note; flagged provider",
                "risk_level": "high",
                "indicators": ["upcoding", "same-day testing", "93000", "93306", "93350", "flagged provider", "excessive procedures", "single visit"]
            },
            {
                "description": "Phantom billing: epidural injections and E/M billed when clinic schedule and EHR show no visits, no consent, no vitals on claimed dates",
                "risk_level": "critical",
                "indicators": ["phantom billing", "no visits", "no consent", "missing documentation", "64483", "flagged provider"]
            },
            {
                "description": "Claims for services on dates when patient was hospitalized elsewhere",
                "risk_level": "critical",
                "indicators": ["date conflict", "hospitalization", "impossible service"]
            },
            {
                "description": "Physical therapy overutilization: prolonged 97110/97112/97140/97530 with no significant improvement and minimal supporting documentation",
                "risk_level": "medium",
                "indicators": ["medical necessity", "overutilization", "97110", "no significant improvement", "minimal supporting", "physical therapy"]
            },
            {
                "description": "Routine established-patient office visit CPT 99213 with wellness exam Z00.00, clean provider, appropriate low amount",
                "risk_level": "low",
                "indicators": ["routine care", "99213", "Z00.00", "appropriate codes", "clean provider", "legitimate"]
            },
            {
                "description": "Legitimate complex neurosurgery: cervical corpectomy 63081 with arthrodesis 22614 and autograft, myelopathy and stenosis documented with MRI correlation and medical necessity",
                "risk_level": "low",
                "indicators": ["63081", "22614", "myelopathy", "spinal stenosis", "well documented", "medical necessity", "legitimate", "neurosurgery"]
            },
            {
                "description": "Standard preventive care claim with proper documentation",
                "risk_level": "low",
                "indicators": ["preventive", "documented", "appropriate", "legitimate"]
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
                "description": "Order with shipping and billing address mismatch using VPN IP and unverified email from OFAC sanctioned country",
                "risk_level": "critical",
                "indicators": ["address mismatch", "vpn", "unverified email", "high risk payment", "ofac country", "nigeria", "ghana", "pakistan", "suspicious"]
            },
            {
                "description": "E-commerce order from OFAC sanctioned or high-risk fraud country with price discrepancy and unverified seller",
                "risk_level": "critical",
                "indicators": ["ofac country", "sanctioned country", "nigeria", "ghana", "pakistan", "bangladesh", "price discrepancy", "unverified seller", "below market price"]
            },
            {
                "description": "New seller offering luxury items 70% below market price with crypto payment and fake reviews",
                "risk_level": "critical",
                "indicators": ["new seller", "below market", "luxury goods", "crypto payment", "fake reviews", "unverified"]
            },
            # High Risk Patterns
            {
                "description": "New seller from OFAC sanctioned country offering luxury items far below market price with no reviews and unverified email",
                "risk_level": "high",
                "indicators": ["new seller", "ofac country", "below market", "luxury goods", "no reviews", "unverified email", "nigeria", "ghana"]
            },
            {
                "description": "Order with shipping address different from billing address using gift card payment",
                "risk_level": "high",
                "indicators": ["address mismatch", "gift card", "payment method", "shipping billing different"]
            },
            {
                "description": "Seller with fake reviews pattern and suspicious shipping location from OFAC country with VPN IP address",
                "risk_level": "high",
                "indicators": ["fake reviews", "suspicious location", "ofac country", "review pattern", "vpn", "ip address", "nigeria", "pakistan"]
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
                "description": "Ghost supplier from OFAC sanctioned country with no verifiable business registration requesting advance payment",
                "risk_level": "critical",
                "indicators": ["ghost supplier", "ofac country", "sanctioned country", "no registration", "unverifiable", "advance payment", "nigeria", "pakistan", "russia"]
            },
            {
                "description": "Supplier from OFAC sanctioned or high-risk fraud country with price inflation and missing documentation",
                "risk_level": "critical",
                "indicators": ["ofac country", "sanctioned country", "high-risk location", "price inflation", "missing documentation", "kickback", "nigeria", "ghana", "pakistan"]
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
                "description": "New supplier from OFAC sanctioned country less than 7 days old requesting advance payment with missing documentation",
                "risk_level": "high",
                "indicators": ["new supplier", "ofac country", "advance payment", "missing documentation", "supplier age", "nigeria", "ghana"]
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


def main():
    """Preload fraud patterns into the Pinecone RAG namespace."""
    logger.info("=" * 70)
    logger.info("🚀 [Pinecone] Starting fraud pattern preload")
    logger.info("=" * 70)

    if not os.getenv("PINECONE_API_KEY"):
        logger.error("❌ [Pinecone] PINECONE_API_KEY environment variable not set")
        sys.exit(1)

    logger.info("✅ [Pinecone] API key found")
    logger.info(f"📦 [Pinecone] Index name: {os.getenv('PINECONE_INDEX_NAME', 'fraudforge-master')}")
    logger.info("")

    logger.info("📋 Loading 'rag' namespace with fraud patterns")
    logger.info("-" * 70)

    try:
        logger.info("🔧 [Pinecone] Initializing RAG engine for namespace: 'rag'")
        rag_engine = RAGEngine(namespace="rag")
        rag_engine.initialize()
        logger.info("✅ [Pinecone] RAG engine ready for namespace 'rag'")
    except Exception as e:
        logger.error(f"❌ [Pinecone] Failed to initialize RAG engine: {e}")
        sys.exit(1)

    all_patterns = get_comprehensive_patterns()
    total_patterns = 0
    for sector, patterns in all_patterns.items():
        logger.info("")
        logger.info(f"📦 [Pinecone] Loading {len(patterns)} patterns for sector: '{sector}'")
        try:
            rag_engine.upsert_patterns(patterns, sector)
            total_patterns += len(patterns)
            logger.info(f"✅ [Pinecone] Sector '{sector}' loaded successfully")
        except Exception as e:
            logger.error(f"❌ [Pinecone] Failed to load sector '{sector}': {e}", exc_info=True)
            sys.exit(1)

    rag_count = rag_engine.get_collection_count()
    logger.info("")
    logger.info("=" * 70)
    logger.info("🎉 [Pinecone] RAG namespace preload complete")
    logger.info(f"   ✅ Patterns upserted: {total_patterns}")
    logger.info(f"   📈 Vectors in 'rag' namespace: {rag_count}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
