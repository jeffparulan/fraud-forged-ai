'use client'

import { motion } from 'framer-motion'
import { Zap, DollarSign, Shield, TrendingUp, Lock, GitBranch, Database, Cloud, Cpu, Sparkles, CheckCircle, ArrowRight } from 'lucide-react'
import Link from 'next/link'

export default function Features() {
  const mainFeatures = [
    {
      icon: Zap,
      title: 'Real-Time Detection',
      description: 'Fast fraud scoring in <2 seconds with explainable AI results',
      details: [
        'Sub-second LLM inference',
        'Concurrent request handling',
        'No processing queues',
        'Live dashboard updates'
      ],
      color: 'text-yellow-400'
    },
    {
      icon: GitBranch,
      title: 'LangGraph Orchestration',
      description: 'Intelligent workflow routing to sector-specific AI models',
      details: [
        'Automatic sector detection',
        'Dynamic model selection',
        'Context-aware routing',
        'Fallback strategies'
      ],
      color: 'text-purple-400'
    },
    {
      icon: Database,
      title: 'RAG-Enhanced Analysis',
      description: 'Pinecone vector search finds similar fraud patterns in milliseconds',
      details: [
        'Cloud vector database (Pinecone)',
        'Pre-loaded fraud patterns',
        'Semantic similarity search',
        'Context enrichment'
      ],
      color: 'text-orange-400'
    },
    {
      icon: Sparkles,
      title: 'Multi-Industry Support',
      description: 'Four cost-optimized fraud-specialized LLMs',
      details: [
        'Banking: Qwen2.5-72B-Instruct (HF Pro - Financial Reasoning)',
        'Healthcare: Two-Stage Pipeline (HF Inference API - Google MedGemma-4B-IT Clinical → Qwen2.5-72B Fraud)',
        'E-commerce: NVIDIA Nemotron-2 (12B VL) (OpenRouter - Marketplace Fraud Detection)',
        'Supply Chain: NVIDIA Nemotron-2 (12B VL) (OpenRouter - Logistics Fraud Detection)'
      ],
      color: 'text-pink-400'
    },
    {
      icon: Shield,
      title: 'Explainable AI',
      description: 'Human-readable explanations for every fraud prediction',
      details: [
        'Risk factor breakdown',
        'Confidence scoring',
        'Similar pattern references',
        'Audit trail generation'
      ],
      color: 'text-blue-400'
    },
    {
      icon: Lock,
      title: 'Enterprise Security',
      description: 'IAP authentication and auto-scaling protection',
      details: [
        'Identity-Aware Proxy',
        'Auto-scale to zero',
        'No database exposure',
        'Cloud-native security'
      ],
      color: 'text-sapphire-400'
    }
  ]

  const technicalFeatures = [
    {
      category: 'Performance',
      features: [
        'Cold start: ~3-4 seconds',
        'Warm requests: <2 seconds (p95)',
        'Concurrent users: 100+',
        'Auto-scaling: Within minutes'
      ]
    },
    {
      category: 'Cost Optimization',
      features: [
        'Minimal infrastructure costs',
        'Scale to zero when idle',
        'No expensive database licenses',
        'No multi-million BPM licenses'
      ]
    },
    {
      category: 'Deployment',
      features: [
        'Streamlined deployment (2-4 hrs)',
        'Infrastructure as Code',
        'CI/CD pipeline included',
        'Zero configuration needed'
      ]
    },
    {
      category: 'Monitoring',
      features: [
        'Health check endpoints',
        'Kill switch status',
        'Request metrics',
        'Error tracking'
      ]
    }
  ]

  const aiCapabilities = [
    {
      title: 'Context-Aware Routing',
      description: 'LangGraph analyzes input context and automatically routes to the most appropriate domain-specific LLM',
      icon: GitBranch
    },
    {
      title: 'RAG Pattern Matching',
      description: 'Pinecone searches 100+ fraud patterns using vector similarity to enrich AI context',
      icon: Database
    },
    {
      title: 'Multi-Model Inference',
      description: 'Cost-optimized fraud detection using HF Pro (Qwen2.5-72B, Two-Stage Google MedGemma-4B-IT+Qwen2.5-72B) and OpenRouter (NVIDIA Nemotron-2 12B VL) with intelligent fallbacks',
      icon: Cpu
    },
    {
      title: 'Explainable Results',
      description: 'Every prediction includes detailed reasoning, risk factors, and similar historical patterns',
      icon: Sparkles
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
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            <span className="gradient-text">Features</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Enterprise-grade capabilities without enterprise platform costs. No compromises.
          </p>
        </motion.div>

        {/* Main Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {mainFeatures.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glass-effect rounded-xl p-6 hover:border-sapphire-500/50 transition-all"
            >
              <feature.icon className={`w-12 h-12 mb-4 ${feature.color}`} />
              <h3 className="text-xl font-bold text-white mb-2">{feature.title}</h3>
              <p className="text-gray-400 mb-4">{feature.description}</p>
              <ul className="space-y-2">
                {feature.details.map((detail) => (
                  <li key={detail} className="flex items-start gap-2 text-sm text-gray-300">
                    <CheckCircle className={`w-4 h-4 mt-0.5 flex-shrink-0 ${feature.color}`} />
                    <span>{detail}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* AI Capabilities */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            AI Capabilities
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {aiCapabilities.map((capability, index) => (
              <motion.div
                key={capability.title}
                initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6"
              >
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-sapphire-500/20 border border-sapphire-500/30 flex-shrink-0">
                    <capability.icon className="w-6 h-6 text-sapphire-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white mb-2">{capability.title}</h3>
                    <p className="text-gray-400">{capability.description}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Technical Specifications */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Technical Specifications
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {technicalFeatures.map((section, index) => (
              <motion.div
                key={section.category}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                className="glass-effect rounded-xl p-6"
              >
                <h3 className="text-lg font-bold text-sapphire-400 mb-4">{section.category}</h3>
                <ul className="space-y-2">
                  {section.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm text-gray-300">
                      <CheckCircle className="w-4 h-4 mt-0.5 text-sapphire-400 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Comparison Highlight */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8 mb-16"
        >
          <h2 className="text-3xl font-bold text-white mb-6 text-center">
            Why FraudForge AI Stands Out
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl font-bold text-amber-400 mb-4">❌ What FraudForge AI is NOT</h3>
              <ul className="space-y-2 text-gray-300">
                <li>• Another SaaS with monthly fees</li>
                <li>• Black box AI you can't customize</li>
                <li>• Vendor lock-in platform</li>
                <li>• Months-long implementation</li>
                <li>• Fixed capacity solution</li>
              </ul>
            </div>
            <div>
              <h3 className="text-xl font-bold text-sapphire-400 mb-4">✅ What FraudForge AI Is</h3>
              <ul className="space-y-2 text-gray-300">
                <li>• 100% open source, you own it</li>
                <li>• Explainable AI you control</li>
                <li>• No vendor, no lock-in</li>
                <li>• Deploy in 2-4 hours</li>
                <li>• Infinite auto-scaling</li>
              </ul>
            </div>
          </div>
        </motion.div>

        {/* Feature Highlights */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mb-16"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-effect rounded-xl p-8 text-center">
              <DollarSign className="w-16 h-16 mx-auto mb-4 text-sapphire-400" />
              <h3 className="text-2xl font-bold text-white mb-2">Save $2M+ Every Year</h3>
              <p className="text-gray-400">Replace closed, million-dollar BPM platforms entirely with open-source GenAI.</p>
            </div>
            <div className="glass-effect rounded-xl p-8 text-center">
              <TrendingUp className="w-16 h-16 mx-auto mb-4 text-blue-400" />
              <h3 className="text-2xl font-bold text-white mb-2">+38-62% Detection Gain</h3>
              <p className="text-gray-400">20-45% false positive reduction vs baseline. How fraud teams measure success.</p>
            </div>
            <div className="glass-effect rounded-xl p-8 text-center">
              <Cloud className="w-16 h-16 mx-auto mb-4 text-purple-400" />
              <h3 className="text-2xl font-bold text-white mb-2">Auto-Scale</h3>
              <p className="text-gray-400">From 0 to 1000+ requests within minutes. Minimal config needed.</p>
            </div>
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
            Experience These Features Live
          </h2>
          <Link href="/detect">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="px-10 py-5 bg-gradient-to-r from-sapphire-600 to-purple-600 text-white rounded-lg font-bold text-xl glow-effect flex items-center gap-2 mx-auto"
            >
              Try Fraud Detection
              <ArrowRight className="w-6 h-6" />
            </motion.button>
          </Link>
        </motion.div>
      </div>
    </div>
  )
}

