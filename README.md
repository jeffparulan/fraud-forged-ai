# FraudForge AI

> **Save $2M+ Every Year. Replace closed, million-dollar BPM platforms entirely with open-source GenAI.**

An open-source GenAI fraud detection platform with streamlined deployment that eliminates expensive BPM platforms. Own your AI infrastructure, not expensive licenses.

## 🎯 Why FraudForge AI?

Traditional fraud detection systems cost $2M+ annually and take months to deploy. FraudForge AI proves companies can **build their own** and eliminate 95%+ of those costs:

- **95%+ Cost Savings** - Minimal cloud infrastructure vs $2M+ annual BPM licensing
- **Affordable AI** - Production LLMs from Hugging Face, OpenRouter, and Google Vertex AI
- **No Database Licenses** - Cloud-based Pinecone RAG, no expensive enterprise databases
- **2-4 Hours Deploy** - Streamlined deployment with Terraform
- **Enterprise-Grade** - Production-ready with auto-scaling, IAP auth, and monitoring
- **You Own It** - 100% open source, zero vendor lock-in


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
# - Backend:  http://localhost:8080
# - API Docs: http://localhost:8080/docs
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

**Next.js Frontend** → **FastAPI Backend** → **LangGraph Router** → **Multi-Provider LLMs** → **Pinecone RAG** → **Fraud Score**

- **Frontend**: Next.js 14 with 4 industry-specific fraud detection forms
- **Backend**: FastAPI + LangGraph intelligent routing + MCP integration
- **AI Models** (Cost-Optimized 2025):
  - Banking: Qwen2.5-72B-Instruct (HF Pro - Financial Reasoning)
  - Medical: Two-Stage Pipeline (HF Inference API - Google MedGemma-4B-IT for Clinical Validation → Qwen2.5-72B for Fraud Analysis)
  - E-commerce: NVIDIA Nemotron-2 (12B VL) (OpenRouter - Marketplace Fraud Detection)
  - Supply Chain: NVIDIA Nemotron-2 (12B VL) (OpenRouter - Logistics Fraud Detection)
  - Fallbacks: Qwen2.5-72B (HF Pro), NVIDIA Nemotron-3-Nano-30B (OpenRouter), Llama-3.1-70B (OpenRouter)
- **RAG**: Pinecone cloud vector database with fraud pattern matching
- **Infrastructure**: Terraform-managed Google Cloud Run (free tier optimized)

[**View Interactive Architecture Diagram →**](/docs/fraud-diagram.html)

## ✨ Features

### Multi-Industry Support
- **🏦 Banking** - Qwen2.5-72B-Instruct (HF Pro) for transaction analysis with financial reasoning
- **🏥 Medical** - Two-Stage Pipeline: Google MedGemma-4B-IT validates clinical legitimacy (diagnosis-procedure compatibility), then Qwen2.5-72B analyzes fraud patterns (upcoding, unbundling, billing anomalies)
- **🛒 E-commerce** - NVIDIA Nemotron-2 (12B VL) (OpenRouter) for online scams with marketplace fraud detection
- **🚚 Supply Chain** - NVIDIA Nemotron-2 (12B VL) (OpenRouter) for compliance fraud with logistics fraud detection

### Intelligent Routing
LangGraph engine automatically:
1. Analyzes input sector and context
2. Routes to optimal domain-specific LLM
3. Queries Pinecone for similar fraud patterns
4. Generates 0-100% fraud score with explanation
5. Returns results in <2 seconds

### Cost-Optimized Operations
- **Auto-Scaling** - Scales to zero when idle (free tier compatible)
- **No BPM Licenses** - Eliminate $2M+ annual platform licensing costs
- **IAP Authentication** - Built-in Google Cloud access control
- **Serverless** - Pay only for actual usage

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
- **Next.js 14** - React SSR with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Sapphire Nightfall Whisper theme
- **Framer Motion** - Smooth animations

### Backend
- **FastAPI** - High-performance Python API
- **LangGraph** - AI workflow orchestration
- **Pinecone** - Cloud vector database for RAG
- **Multi-Provider LLM** - Hugging Face, OpenRouter, Vertex AI

### Infrastructure
- **Terraform** - Infrastructure as Code
- **Google Cloud Run** - Serverless container platform
- **Identity-Aware Proxy** - Zero-cost authentication
- **Cloud Build** - CI/CD pipeline
- **Docker** - Local development and deployment

## 📦 Project Structure

```
fraud-forged-ai/
├── frontend/              # Next.js application
│   ├── app/              # Pages and routes
│   ├── components/       # React components
│   └── lib/             # Utilities
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── core/        # Core business logic
│   │   │   ├── router.py         # LangGraph orchestration
│   │   │   ├── rag_engine.py     # RAG engine
│   │   │   ├── validation.py     # LLM validation
│   │   │   └── explanations.py   # Explanation generation
│   │   ├── llm/         # LLM integration (chains, prompts, providers)
│   │   ├── mcp/         # Model Context Protocol
│   │   └── api/         # FastAPI endpoints
│   └── requirements.txt
├── infrastructure/       # Terraform configs
└── deploy-terraform.sh  # Deployment script
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.

## 🎨 How It Works

1. **User Input** - Submit transaction/claim through industry-specific form
2. **LangGraph Routing** - Routes to optimal sector-specific LLM
3. **RAG Enhancement** - Pinecone retrieves similar fraud patterns
4. **AI Analysis** - LLM processes input with context
5. **Score Generation** - Returns 0-100% fraud score with explanation
6. **Response** - Complete analysis in <2 seconds

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
```

See `.env.example` for all available options.

## 🚦 Deployment

### Local Development

```bash
# Start all services
./run-local.sh

# Services:
# - Frontend: http://localhost:3000
# - Backend:  http://localhost:8080
# - API Docs: http://localhost:8080/docs
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
  "model_used": "Qwen/Qwen2.5-72B-Instruct"
}
```

See API docs at `http://localhost:8080/docs` for full details.

## 📈 Performance

- **Response Time**: <2 seconds (warm requests)
- **Cold Start**: ~3-4 seconds (first request after idle)
- **Auto-Scaling**: Handles 100+ concurrent users
- **Cost**: Free tier compatible, scales as needed

## 🔒 Security

- **IAP Authentication** - Google Cloud Identity-Aware Proxy
- **No Data Persistence** - All data processed in-memory
- **CORS Protection** - Configured for production domains
- **API Key Management** - Secure secrets handling via Terraform

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for deployment security and secrets management.

## 📄 License

MIT License - Use it, modify it, ship it.

---

**Built to prove companies can build their own and save millions.**

Companies spend $500K-$2M/year on Salesforce Apex, Pega BPM, or IBM Fraud Detection. This project proves you can build your own for ~$50K/year using open-source GenAI and modern cloud infrastructure.

[Architecture Diagram](/docs/fraud-diagram.html) | [Deployment Guide](DEPLOYMENT_GUIDE.md)

