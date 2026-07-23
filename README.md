# FraudForge AI

[![CI](https://github.com/jeffparulan/fraud-forged-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/jeffparulan/fraud-forged-ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![Terraform](https://img.shields.io/badge/Terraform-GCP-844FBA?logo=terraform&logoColor=white)

> **Save $2M+ Every Year. Replace closed, million-dollar BPM platforms entirely with open-source GenAI.**

An open-source GenAI fraud detection platform with streamlined deployment that eliminates expensive BPM platforms. Own your AI infrastructure, not expensive licenses.

## 🎯 Why FraudForge AI?

Traditional fraud detection systems cost $2M+ annually and take months to deploy. FraudForge AI proves companies can **build their own** and eliminate 95%+ of those costs:

- **95%+ Cost Savings** - Minimal cloud infrastructure vs $2M+ annual BPM licensing
- **Affordable AI** - Production LLMs from Hugging Face, OpenRouter, and Google Vertex AI
- **No Database Licenses** - Cloud-based Pinecone RAG, no expensive enterprise databases
- **2-4 Hours Deploy** - Streamlined deployment with Terraform
- **Secure by Default** - API-key auth, rate limiting, Secret Manager, auto-scaling
- **You Own It** - 100% open source, zero vendor lock-in

## 🧭 What Makes This Different

Most "LLM + RAG" fraud demos are a single prompt behind a form. FraudForge AI is an **agentic, auditable pipeline**:

1. **6-node auditable LangGraph pipeline** — Every verdict returns a full decision trace (route → MCP enrich → RAG → LLM cross-validation → post-score guardrails → explanation) with per-node latency, RAG similarity scores, and MCP status. You can see *why* the system decided, not just the score.
2. **LLM cross-validation + post-score guardrails** — LLM scores are validated against an independent rule-based engine; OFAC geography, high RAG similarity, and MCP blockchain flags can escalate a too-low score. The response is transparent about which method won.
3. **Two-stage medical pipeline** — Local MedGemma (Mac Mini) validates clinical legitimacy before Nemotron-Super scores fraud, mirroring how real claim reviews separate clinical review from fraud review.
4. **Famous-brand model stack only** — MedGemma, Qwen, Meta, NVIDIA. No random free-tier models. Nemotron-3-Ultra (Finance #16) for e-commerce and supply chain.
5. **Cost-bounded by design** — Budget alerts wired to a kill switch and scale-to-zero Cloud Run keep worst-case spend capped, so the demo can stay live for ~free.


## 🚀 Quick Start

### Run Locally (Development)

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your API keys (Hugging Face, Pinecone, OpenRouter)

# 2. Start services
./run-local.sh

# Access at:
# - Frontend: http://localhost:3000
# - Backend:  http://localhost:8000
# - MCP:      http://localhost:8081
# - API Docs: http://localhost:8000/docs
```

### Deploy to Google Cloud (Production)

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Configure Terraform
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project ID and API keys

# 3. Deploy
cd ..
./deploy-terraform.sh
```

**Deploy time:** 1-2 hours (first time, with prerequisites) | 15-30 minutes (updates)

> **Note**: First-time deployment requires setup of prerequisites (Docker, Terraform, gcloud CLI, API keys). See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete step-by-step instructions.

## 🏗️ Architecture

**Next.js (frontend)** → **FastAPI (backend)** → **LangGraph** → **MCP tools** + **Pinecone RAG** → **LLMs** → **Fraud Score**

Production and local both run **three containers**:

| Service | Image / folder | Role |
|---------|----------------|------|
| `fraud-forge-frontend` | `frontend/` | Next.js UI |
| `fraud-forge-backend` | `backend/` | FastAPI + LangGraph pipeline |
| `fraud-forge-mcp` | `backend/mcp-server/` | Deterministic MCP tool server (wallets, providers, sellers) |

The backend calls MCP over HTTP (`MCP_SERVER_URL`). Soft-fails to `mcp: disabled` if unset. Pinecone uses namespace `rag` for fraud patterns; optional `mcp` namespace for external context preload (separate from the MCP HTTP tools).

### Components
- **Frontend**: Next.js with 4 industry-specific fraud detection forms
- **Backend**: FastAPI + LangGraph (route → MCP enrich → RAG → LLM → guardrails → explain)
- **MCP**: Standalone Cloud Run / Compose service — first-class pipeline stage, not in-process stubs
- **RAG**: Pinecone cloud vector database with fraud pattern matching
- **Infrastructure**: Terraform-managed Google Cloud Run (3 services, free tier optimized)

### AI Models (July 2026)

| Sector | Model | Provider | Purpose |
|--------|-------|----------|----------|
| Banking | Qwen3-32B | HF Inference | Financial reasoning, AML patterns |
| Medical | MedGemma-Local → Nemotron-Super | Local (ngrok) → OpenRouter FREE | Clinical validation → Fraud analysis |
| E-commerce | Nemotron-3-Ultra-550B | OpenRouter FREE | Marketplace fraud (Finance #16) |
| Supply Chain | Nemotron-3-Ultra-550B | OpenRouter FREE | Long-context logistics fraud reasoning |

**Fallback chains** (OpenRouter FREE — MedGemma / Qwen / Meta / NVIDIA brand filter):
- Banking: Nemotron-3-Super-120B → Nemotron-3-Ultra-550B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Medical: Nemotron-Ultra → Nano-30B → Nano-9B → optional HF Qwen3-32B
- E-commerce: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B
- Supply Chain: Nemotron-3-Super-120B → Nemotron-3-Nano-30B → Nemotron-Nano-9B

Note: OpenRouter removed free Qwen/Llama slugs (404). Medical Stage 2 free path is NVIDIA Nemotron.
Medical Stage 1 is local MedGemma via `MEDGEMMA_LOCAL_BASE_URL` / `MEDGEMMA_LOCAL_API_KEY`.
HF Qwen3-32B remains banking primary (and optional medical fallback) when the HF account has Inference credits;
without credits they 402 and fail-fast into the OpenRouter FREE chain above.

[**View Interactive Architecture Diagram →**](https://fraud-forge-frontend-203639324676.us-central1.run.app/docs/fraud-diagram.html)

## ✨ Features

### Multi-Industry Support

| Industry | Model | Capability |
|----------|-------|------------|
| 🏦 Banking | Qwen3-32B (HF Inference) | Transaction analysis with financial reasoning |
| 🏥 Medical | MedGemma-Local → Nemotron-Super | Clinical validation (local) + fraud pattern detection |
| 🛒 E-commerce | Nemotron-3-Ultra-550B (OpenRouter FREE) | Marketplace fraud detection (Finance #16) |
| 🚚 Supply Chain | Nemotron-3-Ultra-550B (OpenRouter FREE) | Logistics compliance fraud detection (1M context) |

### Intelligent Routing

| Step | Action |
|------|--------|
| 1 | Analyze input sector and context |
| 2 | Route to optimal domain-specific LLM |
| 3 | Enrich via MCP tools (wallets / providers / sellers) |
| 4 | Query Pinecone (`rag` namespace) for similar fraud patterns |
| 5 | Cross-validate LLM vs rules + post-score guardrails |
| 6 | Return score, explanation, and decision trace |

### Cost-Optimized Operations

| Feature | Benefit |
|---------|----------|
| Auto-Scaling | Scales to zero when idle (free tier compatible) |
| No BPM Licenses | Eliminate $2M+ annual platform licensing costs |
| API-Key Auth + Rate Limiting | Optional X-API-Key gate and per-IP throttling on the analysis endpoint |
| Serverless | Pay only for actual usage |

## 📊 Use Cases

| Metric | Traditional | FraudForge AI |
|--------|------------|---------------|
| **Setup Time** | 3-6 months | 1-2 hours (with prerequisites) |
| **Annual Cost** | $500K-$2M | ~$1K-$7K (cloud-based) |
| **Customization** | Weeks | Hours to days |
| **Scale** | Fixed capacity | Auto-scale |
| **Vendor Lock-in** | Yes | No |

**Real-World Applications:**
- Fintech startups deploying fraud detection day-one
- Healthcare providers catching fraudulent claims
- E-commerce platforms screening transactions in real-time
- Audit firms automating compliance reviews

## 🛠️ Tech Stack

### Frontend

| Technology | Purpose |
|------------|----------|
| Next.js 14 | React SSR with App Router |
| TypeScript | Type-safe development |
| Tailwind CSS | Sapphire Nightfall Whisper theme |
| Framer Motion | Smooth animations |

### Backend

| Technology | Purpose |
|------------|----------|
| FastAPI | High-performance Python API |
| LangGraph | AI workflow orchestration |
| MCP tool server | External context tools (`backend/mcp-server`) |
| Pinecone | Cloud vector database for RAG (`rag` namespace) |
| Multi-Provider LLM | Hugging Face, OpenRouter |

### Infrastructure

| Technology | Purpose |
|------------|----------|
| Terraform | Infrastructure as Code |
| Google Cloud Run | 3 serverless services (frontend, backend, MCP) |
| Secret Manager | API keys stored securely (Terraform-managed) |
| GitHub Actions | CI: backend tests, frontend build, Terraform validate |
| Docker | Local development and deployment |

## 📦 Project Structure

```
fraud-forged-ai/
├── frontend/                 # Next.js → fraud-forge-frontend
├── backend/                  # FastAPI → fraud-forge-backend
│   ├── app/
│   │   ├── core/             # LangGraph router, RAG, validation, guardrails
│   │   ├── llm/              # models.yaml, orchestrator, prompts
│   │   └── mcp/              # MCP HTTP client (+ optional Pinecone mcp namespace helper)
│   ├── mcp-server/           # Standalone image → fraud-forge-mcp
│   │   ├── Dockerfile
│   │   ├── mcp_server.py
│   │   └── requirements-mcp.txt
│   └── requirements.txt
├── infrastructure/           # Terraform (3 Cloud Run services)
├── docker-compose.yml        # Local: mcp + backend + frontend
└── deploy-terraform.sh       # Build/push/deploy all three images
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.

## 🎨 How It Works

| Step | Description |
|------|-------------|
| 1. User Input | Submit transaction/claim through industry-specific form |
| 2. LangGraph Routing | Routes to optimal sector-specific LLM |
| 3. MCP Enrichment | Backend calls `fraud-forge-mcp` tools for external signals |
| 4. RAG Enhancement | Pinecone `rag` namespace retrieves similar fraud patterns |
| 5. AI Analysis | LLM processes input with MCP + RAG context |
| 6. Guardrails + Score | Cross-validation + OFAC/RAG/MCP floors; decision trace returned |

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
HUGGINGFACE_API_TOKEN=your_token_here
PINECONE_API_KEY=your_key_here
PINECONE_HOST=your_host_here

# Optional (for fallback models)
OPENROUTER_API_KEY=your_key_here

# GCP (for deployment)
GCP_PROJECT_ID=your-project-id

# MCP (optional — compose/deploy set this automatically)
# Host-run backend: MCP_SERVER_URL=http://localhost:8081
# MCP_SERVER_URL=http://localhost:8081
```

See `.env.example` for all available options.

## 🚦 Deployment

### Local Development

```bash
# Start all services
./run-local.sh

# Services:
# - Frontend: http://localhost:3000
# - Backend:  http://localhost:8000
# - MCP:      http://localhost:8081/health
# - API Docs: http://localhost:8000/docs
```

**Requirements:** Docker Desktop

### Production (Google Cloud)

```bash
# 1. Configure Terraform
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project ID and API keys

# 2. Deploy
cd ..
./deploy-terraform.sh
```

**Prerequisites:** 
- Google Cloud account with billing enabled
- Docker Desktop 4.0+
- Terraform 1.5.0+
- Google Cloud SDK (gcloud) 450.0.0+
- jq 1.6+
- API keys: Hugging Face, Pinecone, OpenRouter

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete prerequisites and step-by-step deployment instructions.

## 🎯 API Endpoints

### Fraud Detection
```bash
POST /api/detect
Content-Type: application/json

{
  "sector": "banking",
  "data": { ... }
}

Response:
{
  "fraud_score": 87,
  "risk_level": "high",
  "explanation": "...",
  "model_used": "Qwen3-32B (HF Inference)",
  "risk_factors": ["Unverified KYC", "High-risk country", "..."],
  "decision_trace": [
    {"node": "route_model", "title": "Model routing", "detail": "Sector 'banking' routed to Qwen3-32B (HF Inference)", "status": "ok"},
    {"node": "retrieve_context", "title": "RAG pattern retrieval", "detail": "Matched 5 known fraud pattern(s) in Pinecone", "status": "ok"},
    {"node": "analyze_fraud", "title": "Cross-validation: LLM accepted", "detail": "Qwen3-32B scored 87; accepted after agreement check against rule-based score 82", "status": "ok"},
    {"node": "generate_explanation", "title": "Explanation generated", "detail": "Final verdict: 87/100 (HIGH) via LLM analysis", "status": "ok"}
  ]
}
```

If `FRAUDFORGE_API_KEY` is configured, include the header `X-API-Key: <your-key>`.

See API docs at `http://localhost:8080/docs` for full details.

## 📈 Performance

| Metric | Value |
|--------|-------|
| Response Time | <2 seconds (warm requests) |
| Cold Start | ~3-4 seconds (first request after idle) |
| Auto-Scaling | Handles 100+ concurrent users |
| Cost | Free tier compatible, scales as needed |

## 🔒 Security

| Feature | Description |
|---------|-------------|
| API-Key Auth | Optional `X-API-Key` gate on `/api/detect` (set `FRAUDFORGE_API_KEY`) |
| Rate Limiting | Server-side per-IP sliding window (default 10 req/min) |
| Secret Manager | API keys stored in GCP Secret Manager, referenced by Cloud Run |
| CORS Protection | Origin allowlist via `ALLOWED_ORIGINS` |
| No Data Persistence | All data processed in-memory |
| Kill Switch | Budget alerts can pause the service and scale to zero |

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for deployment security and secrets management.

## 📄 License

MIT License - Use it, modify it, ship it.

---

**Built to prove companies can build their own and save millions.**

Companies spend $500K-$2M/year on Salesforce Apex, Pega BPM, or IBM Fraud Detection. This project proves you can build your own for ~$50K/year using open-source GenAI and modern cloud infrastructure.

[Architecture Diagram](https://fraud-forge-frontend-203639324676.us-central1.run.app/docs/fraud-diagram.html) | [Deployment Guide](DEPLOYMENT_GUIDE.md)

