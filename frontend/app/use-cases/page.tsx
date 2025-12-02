'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { Building2, Heart, ShoppingCart, FileCheck, TrendingUp, DollarSign, Clock, CheckCircle } from 'lucide-react'

export default function UseCases() {
  const useCases = [
    {
      icon: Building2,
      title: 'Banking & Crypto Exchanges',
      description: 'Detect Rug Pulls, AML Risks, ATOs & Synthetics in Seconds—Banking-Proof Your Ops',
      challenge: 'Need enterprise-grade fraud detection but can\'t afford million-dollar platforms',
      solution: 'FraudForge AI delivers Meta: Finance-Llama3-8B powered fraud detection tailored for banking and crypto at reasonable cost and full customizability.',
      results: [
        'Escape $500K–$3M+ annual licensing and consultant lock-in.',
        'Deploy within 2-4 hours with full integration',
        'Scale with business growth automatically',
        '+38-62% detection gain over baseline rules'
      ],
      color: 'sapphire'
    },
    {
      icon: Heart,
      title: 'Healthcare Providers',
      description: 'Catch fraudulent claims before they\'re paid',
      challenge: 'Billions lost annually to medical billing fraud and false claims',
      solution: 'Google\'s MedGemma-4B, a Gemma variant optimized for medical text and image comprehension.',
      results: [
        'Reduce fraud losses by 85%+',
        'Process 10K+ claims per day',
        'Identify unbundling and upcoding',
        'Full audit trail for compliance'
      ],
      color: 'purple'
    },
    {
      icon: ShoppingCart,
      title: 'E-commerce Platforms',
      description: 'Real-time seller/buyer fraud screening',
      challenge: 'Fake sellers, counterfeit products, and review manipulation damage trust',
      solution: 'NVIDIA: Nemotron Nano 12B 2 VL detects scam patterns across listings and user behavior',
      results: [
        '+45-60% detection gain on scam listings',
        'Identify fake review patterns',
        'Protect buyer payment info',
        'Maintain marketplace integrity'
      ],
      color: 'pink'
    },
    {
      icon: FileCheck,
      title: 'Supply Chain & Procurement',
      description: 'Detect supplier fraud and kickback schemes',
      challenge: 'Ghost suppliers, inflated invoices, and kickback schemes cost billions annually',
      solution: 'NVIDIA: Nemotron Nano 12B 2 VL analyzes supplier patterns, pricing anomalies, and documentation gaps',
      results: [
        'Prevent ghost supplier scams',
        'Detect price manipulation',
        'Flag kickback patterns',
        'Verify supplier credentials'
      ],
      color: 'green'
    }
  ]

  const comparison = [
    {
      metric: 'Setup Time',
      traditional: '3-6 months',
      fraudforge: '2-4 hours',
      savings: '99% faster'
    },
    {
      metric: 'Annual Cost',
      traditional: '$500K-$2M',
      fraudforge: 'Minimal Cloud Costs',
      savings: '95%+ savings'
    },
    {
      metric: 'Detection Gain',
      traditional: 'Baseline (0%)',
      fraudforge: '+38-62%',
      savings: 'Lift over baseline'
    },
    {
      metric: 'False Positives',
      traditional: 'High (baseline)',
      fraudforge: '-20-45%',
      savings: 'Reduction vs baseline'
    },
    {
      metric: 'Customization',
      traditional: 'Weeks',
      fraudforge: '2-4 hours',
      savings: '99% faster'
    },
    {
      metric: 'Vendor Lock-in',
      traditional: 'Yes',
      fraudforge: 'No',
      savings: 'Freedom'
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
            <span className="gradient-text">Use Cases</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Real-world applications proving GenAI can democratize fraud detection across industries
          </p>
        </motion.div>

        {/* Use Cases Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-20">
          {useCases.map((useCase, index) => (
            <motion.div
              key={useCase.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="glass-effect rounded-xl p-8 hover:border-sapphire-500/50 transition-all"
            >
              <div className="flex items-start gap-4 mb-6">
                <div className={`p-3 rounded-lg bg-${useCase.color}-500/20 border border-${useCase.color}-500/30`}>
                  <useCase.icon className={`w-8 h-8 text-${useCase.color}-400`} />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white mb-2">{useCase.title}</h3>
                  <p className="text-gray-400">{useCase.description}</p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-amber-400 font-semibold mb-2">❌ Challenge</h4>
                  <p className="text-gray-300">{useCase.challenge}</p>
                </div>

                <div>
                  <h4 className="text-sapphire-400 font-semibold mb-2">✅ Solution</h4>
                  <p className="text-gray-300">{useCase.solution}</p>
                </div>

                <div>
                  <h4 className="text-sapphire-400 font-semibold mb-2">📊 Results</h4>
                  <ul className="space-y-2">
                    {useCase.results.map((result) => (
                      <li key={result} className="flex items-start gap-2 text-gray-300">
                        <CheckCircle className="w-4 h-4 text-sapphire-400 mt-1 flex-shrink-0" />
                        <span>{result}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Comparison Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8 mb-12"
        >
          <h2 className="text-3xl font-bold text-white mb-8 text-center">
            Traditional vs <span className="gradient-text">FraudForge AI</span>
          </h2>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-4 px-4 text-gray-400 font-semibold">Metric</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-semibold">Traditional</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-semibold">FraudForge AI</th>
                  <th className="text-left py-4 px-4 text-gray-400 font-semibold">Impact</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((row, index) => (
                  <tr key={row.metric} className="border-b border-white/5">
                    <td className="py-4 px-4 text-white font-semibold">{row.metric}</td>
                    <td className="py-4 px-4 text-amber-400">{row.traditional}</td>
                    <td className="py-4 px-4 text-sapphire-400">{row.fraudforge}</td>
                    <td className="py-4 px-4 text-sapphire-400 font-semibold">{row.savings}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* ROI Calculator */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-effect rounded-xl p-8 mb-12"
        >
          <h2 className="text-3xl font-bold text-white mb-6 text-center">
            ROI Calculator
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center p-6 bg-amber-500/10 rounded-lg border border-amber-500/30">
              <DollarSign className="w-12 h-12 mx-auto mb-3 text-amber-400" />
              <div className="text-3xl font-bold text-amber-400 mb-2">$2M+</div>
              <div className="text-gray-300">Legacy BPM Platforms</div>
              <div className="text-sm text-gray-400 mt-2">(Annual licensing + hidden fees)</div>
            </div>

            <div className="text-center p-6 bg-sapphire-500/10 rounded-lg border border-sapphire-500/30">
              <TrendingUp className="w-12 h-12 mx-auto mb-3 text-sapphire-400" />
              <div className="text-3xl font-bold text-sapphire-400 mb-2">~$50K</div>
              <div className="text-gray-300">FraudForge AI Cost</div>
              <div className="text-sm text-gray-400 mt-2">(Cloud + AI inference)</div>
            </div>

            <div className="text-center p-6 bg-sapphire-500/10 rounded-lg border border-sapphire-500/30">
              <Clock className="w-12 h-12 mx-auto mb-3 text-sapphire-400" />
              <div className="text-3xl font-bold text-sapphire-400 mb-2">2-4 hrs</div>
              <div className="text-gray-300">Time to Deploy</div>
              <div className="text-sm text-gray-400 mt-2">(vs 3-6 months)</div>
            </div>
          </div>

          <div className="mt-8 p-6 bg-gradient-to-r from-sapphire-500/20 to-purple-500/20 rounded-lg text-center">
            <div className="text-5xl font-bold text-white mb-2">Save $1.95M+</div>
            <div className="text-xl text-gray-300">annually by eliminating BPM platform licensing</div>
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
            Ready to Transform Your Fraud Detection?
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

