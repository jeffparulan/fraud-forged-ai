# FraudForge AI - Architecture

## System Overview

Agentic AI system using LangGraph to orchestrate fraud detection across multiple specialized LLMs with RAG enhancement.

## Architecture

```
FastAPI Backend
├── LangGraph Orchestration (app/core/router.py) — 6-node auditable pipeline
│   ├── 1. Route Model      → Select sector-specific LLM
│   ├── 2. Enrich MCP       → External tools via Model Context Protocol (soft-fail)
│   ├── 3. Retrieve Context → Pinecone RAG + similarity provenance
│   ├── 4. Analyze Fraud    → LLM inference + LLM-vs-rules cross-validation
│   ├── 5. Apply Guardrails → OFAC / high-RAG / MCP escalation floors
│   └── 6. Generate Explain → Verdict + decision_trace + pipeline_meta
├── RAG Engine (app/core/rag_engine.py)
│   └── Pinecone vector search (top/avg similarity, embedding source)
├── Validation (app/core/validation.py)
│   └── LLM vs rule-based validation
└── LLM Client (app/llm/orchestrator.py)
    ├── Config: app/llm/models.yaml (single source of truth)
    ├── Hugging Face (Qwen3-32B — Banking + Medical Stage 2; MedGemma-27B — Medical Stage 1)
    └── OpenRouter (Nemotron-3-Ultra — E-com + Supply; Nemotron-Super / Nano — FREE fallbacks)
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
│   ├── models.yaml        # Model routing + display names (edit here)
│   ├── config.py          # YAML loader + helpers
│   ├── orchestrator.py    # Multi-provider inference
│   ├── chains/            # Sector-specific rule scores
│   ├── prompts/           # Prompts
│   └── embeddings/        # RAG embeddings
├── mcp/                    # Model Context Protocol
├── api/v1/                 # API endpoints
└── main.py
```

## LangGraph Workflow

### 1. Route Model
Select sector-specific LLM (MedGemma / Qwen / Meta / NVIDIA only).

### 2. Enrich MCP
Call Model Context Protocol tools for sector-relevant external signals
(blockchain wallets, provider credentials, seller reputation). Soft-fails if
`MCP_SERVER_URL` is unset or unreachable — never blocks the pipeline.

### 3. Retrieve Context
Query Pinecone for similar fraud patterns. Surfaces top/avg cosine similarity
and embedding provenance (`hf` vs hash fallback) in the decision trace.

### 4. Analyze Fraud
Run LLM inference, validate against rule-based score:
- Accept LLM if score difference < 20 points
- Reject if extreme discrepancy (rule < 10 AND llm > 85)
- Special handling for medical (trust two-stage pipeline)
- Fallback to rule-based if validation fails

### 5. Apply Guardrails
Post-score escalation floors when OFAC geography, high RAG similarity to known
CRITICAL patterns, or MCP blockchain red flags disagree with a low LLM score.

### 6. Generate Explanation
Build human-readable explanation with risk factors.

Every request returns a **decision_trace** (per-node timeline with latency) and
**pipeline_meta** (MCP status, RAG scores, embedding source, guardrail flag).

## Model Selection

| Sector | Model | Provider | Cost |
|--------|-------|----------|------|
| Banking | Qwen3-32B | HF Inference | Pay-per-token |
| Medical | MedGemma-27B → Qwen3-32B | HF Inference (Featherless AI) | Pay-per-token |
| E-commerce | Nemotron-3-Ultra-550B | OpenRouter FREE | Free |
| Supply Chain | Nemotron-3-Ultra-550B | OpenRouter FREE | Free |

**Fallback chains** (OpenRouter FREE — MedGemma / Qwen / Meta / NVIDIA only):
- Banking: Nemotron-3-Super-120B → Nemotron-3-Ultra-550B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Medical: Nemotron-3-Super-120B (if MedGemma/Qwen HF unavailable) → Ultra → Nano
- E-commerce: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Supply Chain: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B

OpenRouter free Qwen/Llama slugs are gone (404). HF large chat models need Inference credits (402 otherwise);
embeddings (MiniLM) still work on HF free for RAG.

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
- Optional API-key auth (`FRAUDFORGE_API_KEY`) + per-IP rate limiting
- Secrets in GCP Secret Manager (Terraform-managed)
- Budget alerts + kill switch at $5

## Performance

- Cold start: ~3-4s (Pinecone init)
- Warm request: <2s
- Throughput: 100+ concurrent requests
