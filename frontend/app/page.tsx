'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { ArrowRight, Zap, DollarSign, Clock, Shield, Sparkles, BarChart3 } from 'lucide-react'

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 px-4 sm:px-6 lg:px-8">
        <div className="absolute inset-0 z-0">
          <div className="absolute inset-0 bg-gradient-to-br from-sapphire-600/20 via-transparent to-purple-600/20" />
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-sapphire-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.5 }}
              className="inline-block mb-6"
            >
              <span className="px-4 py-2 rounded-full text-sm font-semibold bg-sapphire-500/20 text-sapphire-300 border border-sapphire-500/30">
                ✨ Save $2M+ Per Year. Ditch Million-Dollar BPM Platforms.
              </span>
            </motion.div>

            <h1 className="text-5xl md:text-7xl font-bold mb-6 text-white">
              <span className="gradient-text">FraudForge AI</span>
            </h1>

            <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Open-source GenAI fraud detection that deploys in 2-4 hours and replaces million-dollar enterprise platforms.
            </p>

            <p className="text-lg text-gray-400 mb-12 max-w-2xl mx-auto">
              Replace 50,000–150,000 brittle rules with adaptive GenAI. FraudForge learns continuously with &lt;50 guardrails — not rule sprawl.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link href="/detect">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-8 py-4 bg-gradient-to-r from-sapphire-600 to-purple-600 text-white rounded-lg font-semibold text-lg flex items-center gap-2 glow-effect"
                >
                  Try Live Demo
                  <ArrowRight className="w-5 h-5" />
                </motion.button>
              </Link>

              <Link href="/architecture">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-8 py-4 glass-effect text-white rounded-lg font-semibold text-lg flex items-center gap-2"
                >
                  View Architecture
                  <Sparkles className="w-5 h-5" />
                </motion.button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { icon: DollarSign, label: 'Annual Savings', value: '$2M+', color: 'text-sapphire-400' },
              { icon: Clock, label: 'Deploy Time', value: '2-4 hrs', color: 'text-blue-400' },
              { icon: BarChart3, label: 'Guardrails vs Enterprise Rules', value: '<50 vs 63K+', color: 'text-purple-400' },
              { icon: Shield, label: 'No Vendor Lock-in', value: '100%', color: 'text-sapphire-400' },
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1, duration: 0.5 }}
                className="glass-effect rounded-xl p-6 text-center"
              >
                <stat.icon className={`w-12 h-12 mx-auto mb-4 ${stat.color}`} />
                <div className={`text-3xl font-bold mb-2 ${stat.color}`}>{stat.value}</div>
                <div className="text-gray-400">{stat.label}</div>
              </motion.div>
            ))}
          </div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-8 text-center"
          >
            <p className="text-xl text-gray-300 font-semibold italic">
              Why manage a rule graveyard when AI models continuously learn and outperform thousands of hand-written rules?
            </p>
          </motion.div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Legacy BPM vs <span className="gradient-text">FraudForge AI</span>
            </h2>
          </motion.div>

          {/* Side-by-Side Comparison Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="glass-effect rounded-xl p-8"
            >
              <h3 className="text-2xl font-bold text-amber-400 mb-4">Legacy BPM / Rules-Engine Reality</h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>$500K-$2M+ per year in licensing & maintenance</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>40,000-150,000 hand-written if/then rules</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>3-9 months + six figures to change logic</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>One new scheme = 100-500 new rules</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>Rules drift, duplicates, version sprawl</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>Black-box or semi-explainable decisions</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">✗</span>
                  <span>Permanent vendor lock-in & forced upgrades</span>
                </li>
              </ul>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              className="glass-effect rounded-xl p-8 border-2 border-sapphire-500/30"
            >
              <h3 className="text-2xl font-bold text-sapphire-400 mb-4">FraudForge AI Reality</h3>
              <ul className="space-y-3 text-gray-300">
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>$0 licensing — 100% open-source</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>&lt; 50 hard guardrails + LLM-driven reasoning (learned patterns)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>New fraud pattern live in &lt;4 hours</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>One new scheme = 5-20 examples → model retrains</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>Deterministic LangGraph routing + full trace logs</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>100% traceable, regulator-ready reasoning</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-sapphire-500">✓</span>
                  <span>You own the code — zero lock-in</span>
                </li>
              </ul>
            </motion.div>
          </div>

          {/* Rules Bloat Summary */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="glass-effect rounded-xl p-8 text-center border-2 border-purple-500/30"
          >
            <div className="flex items-center justify-center gap-3 mb-4">
              <span className="px-4 py-2 rounded-full text-sm font-semibold bg-sapphire-500/20 text-sapphire-300 border border-sapphire-500/30">
                Rules Bloat Badge
              </span>
              <span className="px-4 py-2 rounded-full text-sm font-semibold bg-sapphire-500/20 text-sapphire-300 border border-sapphire-500/30">
                Save $2M+ Annually
              </span>
            </div>
            <p className="text-xl text-gray-200">
              <span className="text-amber-400 font-bold">63,000+ hand-written rules</span>
              {' → '}
              <span className="text-sapphire-400 font-bold">&lt;50 guardrails + LLM learning</span>
              <span className="text-pink-400 ml-2">❤️</span>
            </p>
            <p className="text-sm text-gray-400 mt-3">
              All fraud pattern detection is learned by LLM models, not hand-coded
            </p>
          </motion.div>
        </div>
      </section>

      {/* Industry Coverage */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Multi-Industry <span className="gradient-text">Coverage</span>
            </h2>
            <p className="text-xl text-gray-300">
              Sector-specific AI models with +38-62% detection gain and 20-45% false positive reduction
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: 'Banking & Crypto',
                model: 'Meta: Finance-Llama3-8B',
                icon: '🏦',
                description: 'Velocity anomalies, mule rings, txn graph divergence, wash trading',
                link: '/detect?sector=banking'
              },
              {
                title: 'Medical Claims',
                model: 'Google: MedGemma-4B',
                icon: '🏥',
                description: 'Upcoding/downcoding, modifier abuse, unbundling, suspect provider behavior',
                link: '/detect?sector=medical'
              },
              {
                title: 'E-commerce',
                model: 'NVIDIA: Nemotron Nano 12B 2 VL',
                icon: '🛒',
                description: 'Return fraud, fake accounts, buyer/seller collusion',
                link: '/detect?sector=ecommerce'
              },
              {
                title: 'Supply Chain',
                model: 'NVIDIA: Nemotron Nano 12B 2 VL',
                icon: '📦',
                description: 'Ghost suppliers, kickback schemes, price manipulation',
                link: '/detect?sector=supply_chain'
              },
            ].map((industry, index) => (
              <Link key={industry.title} href={industry.link}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.05, y: -5 }}
                  className="glass-effect rounded-xl p-6 cursor-pointer transition-all hover:border-sapphire-500/50 h-full flex flex-col"
                >
                  <div className="text-5xl mb-4">{industry.icon}</div>
                  <h3 className="text-xl font-bold text-white mb-2">{industry.title}</h3>
                  <div className="text-sm text-sapphire-400 mb-3 font-mono">{industry.model}</div>
                  <p className="text-gray-400 text-sm flex-grow">{industry.description}</p>
                </motion.div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Technical Excellence */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            className="glass-effect rounded-xl p-12 text-center"
          >
            <h2 className="text-4xl font-bold text-white mb-6">
              Built with <span className="gradient-text">Modern Stack</span>
            </h2>
            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Production-ready AI models from Hugging Face, OpenRouter, and Google Vertex AI • LangGraph orchestration • Pinecone RAG • MCP • FastAPI • Next.js • Terraform
            </p>
            <div className="flex flex-wrap justify-center gap-4 mb-8">
              {['LangGraph', 'Hugging Face', 'OpenRouter AI', 'Google Vertex AI', 'Meta: Finance-Llama3-8B', 'Google: MedGemma-4B', 'NVIDIA: Nemotron Nano 12B 2 VL', 'Pinecone', 'MCP', 'FastAPI', 'Next.js', 'Terraform', 'Cloud Run'].map((tech) => (
                <span key={tech} className="px-4 py-2 bg-sapphire-500/20 text-sapphire-300 rounded-full text-sm font-semibold border border-sapphire-500/30">
                  {tech}
                </span>
              ))}
            </div>
            <Link href="/architecture">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-8 py-4 bg-gradient-to-r from-sapphire-600 to-purple-600 text-white rounded-lg font-semibold text-lg"
              >
                Explore Architecture
              </motion.button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="animated-gradient rounded-2xl p-12 text-center"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to Detect Fraud?
            </h2>
            <p className="text-xl text-gray-100 mb-8">
              Try the live demo and see GenAI fraud detection in action
            </p>
            <Link href="/detect">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-10 py-5 bg-white text-sapphire-700 rounded-lg font-bold text-xl shadow-2xl"
              >
                Launch Detection Platform →
              </motion.button>
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  )
}

