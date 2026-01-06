'use client'

import { motion } from 'framer-motion'
import { FileInput, GitBranch, Database, Cpu, CheckCircle, ArrowRight, Zap } from 'lucide-react'
import Link from 'next/link'

export default function HowItWorks() {
  const steps = [
    {
      number: 1,
      title: 'User Submits Data',
      icon: FileInput,
      description: 'User fills out industry-specific form with transaction, claim, or activity details',
      technical: 'Next.js form validates input client-side, sends POST request to FastAPI backend',
      example: {
        banking: 'Transaction: $15,000 from Nigeria at 3 AM using new device',
        medical: 'Claim: $75,000 with 8 procedures from flagged provider',
        ecommerce: 'Listing: Luxury watch 70% below market, new seller, no reviews',
        supply_chain: 'Order: $150k from 5-day-old supplier, 45% price variance, advance payment'
      },
      color: 'text-blue-400'
    },
    {
      number: 2,
      title: 'LangGraph Routes Request',
      icon: GitBranch,
      description: 'Intelligent orchestration layer analyzes sector and routes to optimal LLM',
      technical: 'LangGraph workflow evaluates input context, retrieves external data via MCP, selects domain-specific model based on sector',
      flow: [
        'Parse input sector (banking/medical/ecommerce/supply_chain)',
        'Map sector to specialized LLM',
        'Initialize workflow state',
        'Retrieve external context via MCP (blockchain, credentials, reputation)',
        'Prepare context for RAG retrieval'
      ],
      color: 'text-purple-400'
    },
    {
      number: 3,
      title: 'RAG Retrieves Context',
      icon: Database,
      description: 'Pinecone searches fraud pattern vectors for similar historical cases',
      technical: 'Vector similarity search finds top 5 most relevant fraud patterns from pre-loaded database',
      ragProcess: [
        'Convert input to embedding vector',
        'Query Pinecone index for sector',
        'Retrieve top 5 similar patterns by cosine similarity',
        'Format results as context string',
        'Enrich LLM prompt with fraud pattern examples'
      ],
      color: 'text-orange-400'
    },
    {
      number: 4,
      title: 'AI Analyzes Fraud',
      icon: Cpu,
      description: 'Cost-optimized fraud-specialized LLM with RAG-enhanced context',
      technical: 'HF Pro and OpenRouter FREE models evaluate fraud indicators using specialized reasoning',
      models: {
        banking: 'Qwen2.5-72B (HF Pro) analyzes amount, location, device, timing, account age with financial reasoning',
        medical: 'Two-Stage: Google MedGemma-4B-IT validates clinical legitimacy (diagnosis-procedure match), then Qwen2.5-72B analyzes fraud patterns (upcoding, billing behavior)',
        ecommerce: 'NVIDIA Nemotron-2 (12B VL) (OpenRouter) evaluates seller age, pricing, reviews, shipping with marketplace fraud detection',
        supply_chain: 'NVIDIA Nemotron-2 (12B VL) (OpenRouter) examines supplier age, price variance, payment terms, documentation with logistics fraud detection'
      },
      color: 'text-sapphire-400'
    },
    {
      number: 5,
      title: 'Generate Score & Explanation',
      icon: CheckCircle,
      description: 'Returns 0-100% fraud probability with human-readable reasoning',
      technical: 'Converts risk factors into score, maps to risk level, generates natural language explanation',
      output: {
        fraud_score: 87,
        risk_level: 'high',
        explanation: 'Qwen2.5-72B analysis identifies high risk using financial reasoning. Red flags detected: unusually high transaction amount ($15,000), transaction from Nigeria (OFAC high-risk country), new or unrecognized device, transaction at 3:00 AM, account age only 2 days.',
        model_used: 'Qwen/Qwen2.5-72B-Instruct',
        processing_time_ms: 1847,
        similar_patterns: 5
      },
      color: 'text-yellow-400'
    },
    {
      number: 6,
      title: 'Display Results',
      icon: Zap,
      description: 'Frontend receives response and displays interactive fraud report',
      technical: 'React component renders score gauge, risk badge, explanation, and similar patterns',
      ui: [
        'Animated circular progress for fraud score',
        'Color-coded risk level badge',
        'Detailed explanation with bullet points',
        'Model attribution',
        'Processing time metrics'
      ],
      color: 'text-pink-400'
    }
  ]

  const architectureFlow = [
    { from: 'Browser', to: 'Next.js Frontend', tech: 'React SSR' },
    { from: 'Next.js', to: 'Cloud Run', tech: 'HTTPS POST' },
    { from: 'Cloud Run', to: 'FastAPI', tech: 'Uvicorn' },
    { from: 'FastAPI', to: 'LangGraph', tech: 'Workflow Engine' },
    { from: 'LangGraph', to: 'Pinecone', tech: 'Vector Search' },
    { from: 'LangGraph', to: 'MCP', tech: 'External Context' },
    { from: 'MCP', to: 'LangGraph', tech: 'Tool Results' },
    { from: 'LangGraph', to: 'LLM', tech: 'Sector Model' },
    { from: 'LLM', to: 'LangGraph', tech: 'Fraud Score' },
    { from: 'LangGraph', to: 'FastAPI', tech: 'Response' },
    { from: 'FastAPI', to: 'Frontend', tech: 'JSON' }
  ]

  return (
    <div className="min-h-screen py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-16"
        >
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            <span className="gradient-text">How It Works</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            From user input to fraud verdict in 6 steps. Complete analysis in under 2 seconds.
          </p>
        </motion.div>

        {/* Main Steps */}
        <div className="space-y-8 mb-16">
          {steps.map((step, index) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.15 }}
              className="glass-effect rounded-xl p-8"
            >
              <div className="flex flex-col md:flex-row gap-6">
                {/* Step Number & Icon */}
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 rounded-full bg-sapphire-500/20 border-2 border-sapphire-500/50 flex items-center justify-center mb-4">
                    <span className="text-2xl font-bold text-sapphire-400">{step.number}</span>
                  </div>
                  <step.icon className={`w-12 h-12 ${step.color}`} />
                </div>

                {/* Content */}
                <div className="flex-1">
                  <h3 className="text-2xl font-bold text-white mb-3">{step.title}</h3>
                  <p className="text-gray-300 mb-4 text-lg">{step.description}</p>

                  <div className="bg-nightfall-900/50 rounded-lg p-4 mb-4">
                    <div className="text-sm text-gray-400 mb-1">Technical Implementation:</div>
                    <div className="text-gray-200">{step.technical}</div>
                  </div>

                  {/* Additional Details */}
                  {step.example && (
                    <div className="space-y-2">
                      <div className="text-sm font-semibold text-sapphire-400">Example Inputs:</div>
                      {Object.entries(step.example).map(([sector, text]) => (
                        <div key={sector} className="text-sm text-gray-400">
                          <span className="text-gray-300 font-mono">{sector}:</span> {text}
                        </div>
                      ))}
                    </div>
                  )}

                  {step.flow && (
                    <div>
                      <div className="text-sm font-semibold text-sapphire-400 mb-2">Process Flow:</div>
                      <ul className="space-y-1">
                        {step.flow.map((item, i) => (
                          <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                            <ArrowRight className="w-4 h-4 mt-0.5 text-purple-400 flex-shrink-0" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {step.ragProcess && (
                    <div>
                      <div className="text-sm font-semibold text-sapphire-400 mb-2">RAG Process:</div>
                      <ul className="space-y-1">
                        {step.ragProcess.map((item, i) => (
                          <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                            <ArrowRight className="w-4 h-4 mt-0.5 text-orange-400 flex-shrink-0" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {step.models && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {Object.entries(step.models).map(([sector, description]) => (
                        <div key={sector} className="bg-nightfall-900/30 rounded p-3">
                          <div className="text-sm font-semibold text-sapphire-400 mb-1">{sector}</div>
                          <div className="text-xs text-gray-400">{description}</div>
                        </div>
                      ))}
                    </div>
                  )}

                  {step.output && (
                    <div className="bg-nightfall-950 rounded-lg p-4 font-mono text-sm overflow-x-auto max-w-full">
                      <pre className="text-sapphire-400 whitespace-pre-wrap break-words">{JSON.stringify(step.output, null, 2)}</pre>
                    </div>
                  )}

                  {step.ui && (
                    <div>
                      <div className="text-sm font-semibold text-sapphire-400 mb-2">UI Components:</div>
                      <ul className="space-y-1">
                        {step.ui.map((item, i) => (
                          <li key={i} className="text-sm text-gray-300 flex items-start gap-2">
                            <CheckCircle className="w-4 h-4 mt-0.5 text-pink-400 flex-shrink-0" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>

              {/* Connection Arrow */}
              {index < steps.length - 1 && (
                <div className="flex justify-center mt-6">
                  <div className="w-1 h-8 bg-gradient-to-b from-sapphire-500/50 to-transparent"></div>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Architecture Flow */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8 mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Technical Architecture Flow
          </h2>
          <div className="space-y-3">
            {architectureFlow.map((flow, index) => (
              <motion.div
                key={`${flow.from}-${flow.to}`}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center gap-4 bg-nightfall-900/30 rounded-lg p-4"
              >
                <div className="text-sapphire-400 font-semibold w-32 text-right">{flow.from}</div>
                <ArrowRight className="w-6 h-6 text-gray-500 flex-shrink-0" />
                <div className="text-purple-400 font-semibold w-32">{flow.to}</div>
                <div className="flex-1 text-gray-400 text-sm font-mono">{flow.tech}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Key Technologies */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Key Technologies Explained
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'LangGraph',
                description: 'Workflow orchestration framework that manages multi-step AI processes. Routes requests, coordinates MCP context retrieval, RAG retrieval, and handles model selection.',
                why: 'Makes the system intelligent and adaptable with external context integration'
              },
              {
                title: 'Pinecone',
                description: 'Cloud vector database for semantic search. Stores fraud pattern embeddings and enables fast similarity matching with scalable infrastructure.',
                why: 'Provides context awareness to AI models with cloud scalability'
              },
              {
                title: 'MCP Server',
                description: 'Model Context Protocol provides external context tools (blockchain validation, transaction history, provider credentials, seller reputation).',
                why: 'Enriches fraud detection with real-world data'
              }
            ].map((tech, index) => (
              <motion.div
                key={tech.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6"
              >
                <h3 className="text-xl font-bold text-sapphire-400 mb-3">{tech.title}</h3>
                <p className="text-gray-300 mb-4">{tech.description}</p>
                <div className="text-sm text-gray-400">
                  <span className="text-sapphire-400 font-semibold">Why it matters:</span> {tech.why}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Performance Metrics */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8 mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Performance Metrics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { label: 'Avg Response Time', value: '1.8s', color: 'text-sapphire-400' },
              { label: 'Cold Start', value: '3-4s', color: 'text-yellow-400' },
              { label: 'Detection Gain', value: '+38-62%', color: 'text-blue-400' },
              { label: 'False Positives', value: '-20-45%', color: 'text-purple-400' }
            ].map((metric) => (
              <div key={metric.label} className="text-center">
                <div className={`text-4xl font-bold mb-2 ${metric.color}`}>{metric.value}</div>
                <div className="text-gray-400 text-sm">{metric.label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <h2 className="text-3xl font-bold text-white mb-6">
            See It In Action
          </h2>
          <Link href="/detect">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-10 py-5 bg-gradient-to-r from-sapphire-600 to-purple-600 text-white rounded-lg font-bold text-xl glow-effect"
            >
              Try Live Demo →
            </motion.button>
          </Link>
        </motion.div>
      </div>
    </div>
  )
}

