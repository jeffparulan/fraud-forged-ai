'use client'

import { motion } from 'framer-motion'
import Image from 'next/image'
import Logo from '@/components/Logo'
import { Database, Cpu, Zap, Shield, GitBranch, Box, Cloud, Lock } from 'lucide-react'
import { useModelSummary, SectorId } from '@/lib/models'

export default function Architecture() {
  const { summary } = useModelSummary()
  const sectorOrder: SectorId[] = ['banking', 'medical', 'ecommerce', 'supply_chain']
  const modelColors = ['text-yellow-400', 'text-emerald-400', 'text-purple-400', 'text-orange-400']

  const techStack = [
    {
      category: 'Frontend',
      icon: Box,
      technologies: [
        { name: 'Next.js 14', description: 'React SSR with App Router', color: 'text-blue-400' },
        { name: 'TypeScript', description: 'Type-safe development', color: 'text-blue-400' },
        { name: 'Tailwind CSS', description: 'Sapphire Nightfall theme', color: 'text-cyan-400' },
        { name: 'Framer Motion', description: 'Smooth animations', color: 'text-purple-400' }
      ]
    },
    {
      category: 'Backend',
      icon: Cpu,
      technologies: [
        { name: 'FastAPI', description: 'High-performance Python API', color: 'text-sapphire-400' },
        { name: 'LangGraph', description: 'AI workflow orchestration', color: 'text-emerald-400' },
        { name: 'Pinecone', description: 'Cloud vector database', color: 'text-orange-400' },
        { name: 'MCP', description: 'Model Context Protocol', color: 'text-cyan-400' },
        { name: 'Pydantic', description: 'Data validation', color: 'text-pink-400' }
      ]
    },
    {
      category: 'AI Models',
      icon: Zap,
      technologies: sectorOrder.map((sector, i) => ({
        name: summary[sector]?.primary?.split('(')[0]?.trim() || sector,
        description: summary[sector]?.blurb || summary[sector]?.label || sector,
        color: modelColors[i],
      }))
    },
    {
      category: 'Infrastructure',
      icon: Cloud,
      technologies: [
        { name: 'Google Cloud Run', description: '3 services: frontend, backend, MCP', color: 'text-blue-400' },
        { name: 'Terraform', description: 'Infrastructure as Code', color: 'text-purple-400' },
        { name: 'Secret Manager', description: 'API keys stored securely', color: 'text-sapphire-400' },
        { name: 'Artifact Registry', description: 'mcp / backend / frontend images', color: 'text-orange-400' }
      ]
    }
  ]

  const dataFlow = [
    {
      step: 1,
      title: 'User Input',
      description: 'User submits transaction/claim/activity through industry-specific form',
      icon: Shield,
      color: 'text-sapphire-400'
    },
    {
      step: 2,
      title: 'API Gateway',
      description: 'Next.js frontend sends request to FastAPI backend on Cloud Run',
      icon: Cloud,
      color: 'text-purple-400'
    },
    {
      step: 3,
      title: 'LangGraph Routing',
      description: 'Intelligent router analyzes sector and routes to optimal LLM',
      icon: GitBranch,
      color: 'text-green-400'
    },
    {
      step: 4,
      title: 'MCP Enrichment',
      description: 'Backend calls fraud-forge-mcp tools for wallets, credentials, and seller signals',
      icon: Box,
      color: 'text-cyan-400'
    },
    {
      step: 5,
      title: 'RAG Enhancement',
      description: 'Pinecone rag namespace retrieves similar fraud patterns from vector database',
      icon: Database,
      color: 'text-orange-400'
    },
    {
      step: 6,
      title: 'AI Analysis',
      description: 'Sector-specific LLM processes input with MCP + RAG context',
      icon: Zap,
      color: 'text-yellow-400'
    },
    {
      step: 7,
      title: 'Score & Explain',
      description: 'Guardrails + 0-100% fraud score with decision trace',
      icon: Shield,
      color: 'text-pink-400'
    }
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
          <div className="flex items-center justify-center gap-4 mb-6">
            <Logo size={64} showText={true} animated={true} />
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            <span className="gradient-text">Architecture</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Modern, scalable, cost-optimized architecture built with open-source technologies
          </p>
        </motion.div>

        {/* Architecture Diagram Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-effect rounded-xl p-8 mb-16 text-center"
        >
          <h2 className="text-3xl font-bold text-white mb-4">
            Interactive Architecture Diagram
          </h2>
          <p className="text-gray-300 mb-6">
            Click below to view the architecture diagram
          </p>
          <a
            href="/docs/fraud-diagram.html"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block"
          >
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-8 py-4 bg-gradient-to-r from-sapphire-600 to-purple-600 text-white rounded-lg font-semibold text-lg glow-effect"
            >
              View Architecture Diagram →
            </motion.button>
          </a>
        </motion.div>

        {/* Tech Stack */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Technology Stack
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {techStack.map((stack, index) => (
              <motion.div
                key={stack.category}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6"
              >
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 rounded-lg bg-sapphire-500/20 border border-sapphire-500/30">
                    <stack.icon className="w-6 h-6 text-sapphire-400" />
                  </div>
                  <h3 className="text-2xl font-bold text-white">{stack.category}</h3>
                </div>

                <div className="space-y-4">
                  {stack.technologies.map((tech, index) => (
                    <div key={`${tech.name}-${index}`} className="border-l-2 border-white/10 pl-4">
                      <div className={`font-semibold ${tech.color}`}>{tech.name}</div>
                      <div className="text-gray-400 text-sm">{tech.description}</div>
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Data Layer */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            📊 Data Sources
          </h2>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="glass-effect rounded-xl p-8"
          >
            <p className="text-lg text-gray-300 mb-6 text-center">
              Supports ingestion from:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { name: 'Claims Systems', formats: ['EDI X12', 'HL7', 'FHIR'], icon: '🏥' },
                { name: 'Banking Ledgers', formats: ['ISO8583', 'SWIFT', 'ACH'], icon: '🏦' },
                { name: 'E-commerce Events', formats: ['JSON', 'Webhooks', 'API'], icon: '🛒' },
                { name: 'Supply Chain Telemetry', formats: ['IoT', 'ERP', 'SCM'], icon: '📦' },
                { name: 'Batch Uploads', formats: ['CSV', 'Parquet', 'JSON'], icon: '📄' },
                { name: 'Streaming', formats: ['Pub/Sub', 'Kafka', 'SQS'], icon: '⚡' }
              ].map((source, index) => (
                <motion.div
                  key={source.name}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="border border-white/10 rounded-lg p-4 hover:border-sapphire-500/50 transition-colors"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">{source.icon}</span>
                    <h3 className="font-semibold text-white">{source.name}</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {source.formats.map((format) => (
                      <span
                        key={format}
                        className="px-2 py-1 text-xs bg-sapphire-500/20 text-sapphire-300 rounded border border-sapphire-500/30"
                      >
                        {format}
                      </span>
                    ))}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </motion.div>

        {/* Data Flow */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Request Flow
          </h2>

          <div className="space-y-6">
            {dataFlow.map((flow, index) => (
              <motion.div
                key={flow.step}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6 flex items-start gap-4"
              >
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-sapphire-500/20 border-2 border-sapphire-500/50 flex items-center justify-center">
                    <span className="text-xl font-bold text-sapphire-400">{flow.step}</span>
                  </div>
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <flow.icon className={`w-6 h-6 ${flow.color}`} />
                    <h3 className="text-xl font-bold text-white">{flow.title}</h3>
                  </div>
                  <p className="text-gray-300">{flow.description}</p>
                </div>

                {index < dataFlow.length - 1 && (
                  <div className="hidden md:block">
                    <div className="w-8 h-8 text-sapphire-500">→</div>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Key Features */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Architectural Highlights
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Lock,
                title: 'Cost-Optimized Operations',
                description: 'Google Cloud Run with auto-scale to zero. Minimal costs vs $2M+ BPM licensing.',
                color: 'text-sapphire-400'
              },
              {
                icon: Zap,
                title: 'Vector RAG with Pinecone',
                description: 'Pinecone cloud vector database stores fraud patterns and MCP context. Fast semantic similarity search for context enrichment.',
                color: 'text-yellow-400'
              },
              {
                icon: GitBranch,
                title: 'LangGraph Routing',
                description: 'Intelligent workflow orchestration routes to optimal sector-specific LLMs.',
                color: 'text-purple-400'
              },
              {
                icon: Cloud,
                title: 'Serverless Scale',
                description: 'Automatically scales from 0 to 1000+ concurrent requests. Pay only for actual usage.',
                color: 'text-blue-400'
              },
              {
                icon: Database,
                title: 'Vector Database (Pinecone)',
                description: 'Cloud vector database for RAG pattern matching and MCP context storage. Scalable semantic search.',
                color: 'text-orange-400'
              }
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6"
              >
                <feature.icon className={`w-10 h-10 mb-4 ${feature.color}`} />
                <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Infrastructure Code */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8"
        >
          <div className="flex items-center gap-4 mb-6">
            <h2 className="text-3xl font-bold text-white">
              Infrastructure as Code
            </h2>
            <div className="relative w-10 h-10 flex items-center justify-center">
              <Image 
                src="/terraform-icon.svg" 
                alt="Terraform" 
                width={40}
                height={40}
                className="object-contain"
                unoptimized
              />
            </div>
          </div>
          <p className="text-gray-300 mb-6">
            Everything deployed with Terraform. One command, full stack:
          </p>
          <div className="bg-nightfall-950 rounded-lg p-6 font-mono text-sm overflow-x-auto">
            <div className="text-gray-400"># Deploy entire platform</div>
            <div className="text-sapphire-400">$ ./deploy-terraform.sh</div>
            <div className="text-gray-500 mt-4"># Behind the scenes:</div>
            <div className="text-sapphire-400">docker build/push fraud-forge-mcp</div>
            <div className="text-sapphire-400">docker build/push fraud-forge-backend</div>
            <div className="text-sapphire-400">docker build/push fraud-forge-frontend</div>
            <div className="text-sapphire-400">terraform apply  # 3 Cloud Run services</div>
            <div className="text-gray-500 mt-4"># Output:</div>
            <div className="text-sapphire-400">✓ MCP tool server deployed to Cloud Run</div>
            <div className="text-sapphire-400">✓ Backend deployed (MCP_SERVER_URL wired)</div>
            <div className="text-sapphire-400">✓ Frontend deployed to Cloud Run</div>
            <div className="text-sapphire-400">✓ Cost-optimized infrastructure ready</div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

