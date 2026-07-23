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
    ├── Local MedGemma (Mac Mini / ngrok — Medical Stage 1 clinical audit)
    ├── Hugging Face (Qwen3-32B — Banking primary; optional medical fallback)
    └── OpenRouter (Nemotron-Super — Medical Stage 2; Nemotron-Ultra — E-com + Supply; Nano fallbacks)
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
(blockchain wallets, provider credentials, seller reputation). Local compose and
Cloud Run deploy a free deterministic MCP tool server (`fraud-forge-mcp`). Soft-fails if
`MCP_SERVER_URL` is unset or unreachable — never blocks the pipeline. Decision
trace reports `mcp_status`: `ok` | `no_signals` | `disabled` | `unreachable` | `error`.

### 3. Retrieve Context
Query Pinecone for similar fraud patterns. Surfaces top/avg cosine similarity
and embedding provenance (`hf` vs hash fallback) in the decision trace.

### 4. Analyze Fraud
Medical two-stage (after MCP + Pinecone RAG already ran):
1. Stage 1 local MedGemma clinical audit (Mac Mini via ngrok; optional if unavailable)
2. Stage 2 Nemotron-Super fraud analysis with RAG + MCP (OpenRouter FREE)
3. If Stage 2 fails → Ultra / Nano / optional HF Qwen fallbacks, or rule blend when Stage 1 succeeded

Run LLM inference, validate against rule-based score:
- Medical: accept unless extreme cross-level reversal
- Others: reject on large risk-band reversals
- Fallback to rule-based if no usable LLM score

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
| Medical | MedGemma-Local → Nemotron-Super | Local (ngrok) → OpenRouter FREE | Local + free |
| E-commerce | Nemotron-3-Ultra-550B | OpenRouter FREE | Free |
| Supply Chain | Nemotron-3-Ultra-550B | OpenRouter FREE | Free |

**Fallback chains** (OpenRouter FREE — MedGemma / Qwen / Meta / NVIDIA brand filter):
- Banking: Nemotron-3-Super-120B → Nemotron-3-Ultra-550B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Medical: Nemotron-Ultra → Nano-30B → Nano-9B → optional HF Qwen3-32B
- E-commerce: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Supply Chain: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B

OpenRouter free Qwen/Llama slugs are gone (404). HF large chat models need Inference credits (402 otherwise);
embeddings (MiniLM) still work on HF free for RAG. Medical Stage 1 uses `MEDGEMMA_LOCAL_*` env (Mac Mini).

## Validation Logic

**Medical**: MedGemma-Local Stage 1 (clinical) → Nemotron-Super Stage 2 (fraud); trust two-stage pipeline unless extreme risk-band reversal

**Others**:
- Reject if: rule < 10 AND llm > 85 (false positive)
- Reject if: rule > 60 AND llm < 30 (false negative)
- Reject if: score_diff > 20 (large discrepancy)
- Accept otherwise

## Deployment

**Local**: Docker Compose — three services
- `mcp` → `http://localhost:8081` (`backend/mcp-server`)
- `backend` → `http://localhost:8000` (`MCP_SERVER_URL=http://mcp:8080`)
- `frontend` → `http://localhost:3000`

**Production**: GCP Cloud Run — three services
- `fraud-forge-mcp` — deterministic MCP tool server (image from `backend/mcp-server`)
- `fraud-forge-backend` — FastAPI + LangGraph; env `MCP_SERVER_URL` → MCP service URL
- `fraud-forge-frontend` — Next.js UI
- Auto-scaling / scale-to-zero (free tier friendly)
- Optional API-key auth (`FRAUDFORGE_API_KEY`) + per-IP rate limiting
- Secrets in GCP Secret Manager (Terraform-managed)
- Budget alerts + kill switch at $5

## Performance

- Cold start: ~3-4s (Pinecone init)
- Warm request: <2s
- Throughput: 100+ concurrent requests
