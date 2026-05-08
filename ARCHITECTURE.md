# FraudForge AI - Architecture

## System Overview

Agentic AI system using LangGraph to orchestrate fraud detection across multiple specialized LLMs with RAG enhancement.

## Architecture

```
FastAPI Backend
├── LangGraph Orchestration (app/core/router.py)
│   ├── 1. Route Model      → Select sector-specific LLM
│   ├── 2. Retrieve Context → Query Pinecone RAG
│   ├── 3. Analyze Fraud    → LLM inference + validation
│   └── 4. Generate Explain → Build output
├── RAG Engine (app/core/rag_engine.py)
│   └── Pinecone vector search
├── Validation (app/core/validation.py)
│   └── LLM vs rule-based validation
└── LLM Providers (app/llm/providers/)
    ├── Hugging Face (Qwen3-32B — Banking + Medical Stage 2; MedGemma-27B — Medical Stage 1)
    └── OpenRouter (Nemotron-Super-120B — E-com/Supply Chain; GPT-OSS-120B — fallbacks)
```

## Directory Structure

```
backend/app/
├── core/                   # Core business logic
│   ├── router.py          # LangGraph orchestration
│   ├── rag_engine.py      # RAG engine
│   ├── validation.py      # LLM validation
│   ├── explanations.py    # Explanation generation
│   └── security.py
├── llm/                    # LLM integration
│   ├── chains/            # Sector-specific chains
│   ├── prompts/           # Prompts
│   └── providers/         # Provider clients
├── mcp/                    # Model Context Protocol
├── api/v1/                 # API endpoints
└── main.py
```

## LangGraph Workflow

### 1. Route Model
Select sector-specific LLM:
- Banking → Qwen3-32B (HF Inference — financial reasoning, AML)
- Medical → Two-stage: MedGemma-27B (HF Inference/Featherless AI — clinical validation) → Qwen3-32B (HF Inference — fraud analysis)
- E-commerce → Nemotron-Super-120B (OpenRouter FREE — marketplace fraud)
- Supply Chain → Nemotron-Super-120B (OpenRouter FREE — logistics fraud)

### 2. Retrieve Context
Query Pinecone for similar fraud patterns using embeddings.

### 3. Analyze Fraud
Run LLM inference, validate against rule-based score:
- Accept LLM if score difference < 20 points
- Reject if extreme discrepancy (rule < 10 AND llm > 85)
- Special handling for medical (trust two-stage pipeline)
- Fallback to rule-based if validation fails

### 4. Generate Explanation
Build human-readable explanation with risk factors.

## Model Selection

| Sector | Model | Provider | Cost |
|--------|-------|----------|------|
| Banking | Qwen3-32B | HF Inference | Pay-per-token |
| Medical | MedGemma-27B → Qwen3-32B | HF Inference (Featherless AI) | Pay-per-token |
| E-commerce | Nemotron-Super-120B | OpenRouter FREE | Free |
| Supply Chain | Nemotron-Super-120B | OpenRouter FREE | Free |

**Fallback chains** (all OpenRouter FREE):
- Banking: GPT-OSS-120B → Tencent Hy3 Preview → Llama-3.3-70B
- Medical: GPT-OSS-120B (if MedGemma gated) → Tencent Hy3 Preview → Nemotron-Super-120B
- E-commerce / Supply Chain: GPT-OSS-120B → Tencent Hy3 Preview → Gemma-4-31B

## Validation Logic

**Medical**: MedGemma-27B Stage 1 (clinical) → Qwen3-32B Stage 2 (fraud); trust two-stage pipeline unless extreme discrepancy (rule > 75 AND llm < 25)

**Others**:
- Reject if: rule < 10 AND llm > 85 (false positive)
- Reject if: rule > 60 AND llm < 30 (false negative)
- Reject if: score_diff > 20 (large discrepancy)
- Accept otherwise

## Deployment

**Local**: Docker Compose (FastAPI + Next.js)

**Production**: GCP Cloud Run
- Auto-scaling 0-10 instances
- IAP authentication
- Budget alerts + kill switch at $5

## Performance

- Cold start: ~3-4s (Pinecone init)
- Warm request: <2s
- Throughput: 100+ concurrent requests
