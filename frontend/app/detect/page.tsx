'use client'

import { useState, Suspense } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Building2, Heart, ShoppingCart, Package, Loader } from 'lucide-react'
import BankingForm from '@/components/forms/BankingForm'
import MedicalForm from '@/components/forms/MedicalForm'
import EcommerceForm from '@/components/forms/EcommerceForm'
import SupplyChainForm from '@/components/forms/SupplyChainForm'
import ResultDisplay from '@/components/ResultDisplay'
import { FraudDetectionResponse } from '@/lib/api'

type Sector = 'banking' | 'medical' | 'ecommerce' | 'supply_chain'

export default function DetectPage() {
  const [activeSector, setActiveSector] = useState<Sector>('banking')
  const [result, setResult] = useState<FraudDetectionResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const sectors = [
    {
      id: 'banking' as Sector,
      name: 'Banking & Crypto',
      icon: Building2,
      model: 'Meta: Finance-Llama3-8B',
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
      borderColor: 'border-blue-500/30'
    },
    {
      id: 'medical' as Sector,
      name: 'Medical Claims',
      icon: Heart,
      model: 'Google: MedGemma-4B',
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/20',
      borderColor: 'border-amber-500/30'
    },
    {
      id: 'ecommerce' as Sector,
      name: 'E-commerce',
      icon: ShoppingCart,
      model: 'NVIDIA: Nemotron Nano 12B 2 VL',
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
      borderColor: 'border-purple-500/30'
    },
    {
      id: 'supply_chain' as Sector,
      name: 'Supply Chain',
      icon: Package,
      model: 'NVIDIA: Nemotron Nano 12B 2 VL',
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/20',
      borderColor: 'border-orange-500/30'
    }
  ]

  const handleResult = (response: FraudDetectionResponse) => {
    setResult(response)
    setLoading(false)
  }

  const handleLoading = (isLoading: boolean) => {
    setLoading(isLoading)
    if (isLoading) {
      setResult(null)
    }
  }

  const handleReset = () => {
    setResult(null)
    setLoading(false)
  }

  return (
    <div className="min-h-screen py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
            <span className="gradient-text">Fraud Detection</span>
          </h1>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Select your industry and submit data for real-time AI-powered fraud analysis
          </p>
        </motion.div>

        {/* Sector Tabs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
          {sectors.map((sector, index) => (
            <motion.button
              key={sector.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => {
                setActiveSector(sector.id)
                handleReset()
              }}
              className={`p-6 rounded-xl transition-all ${
                activeSector === sector.id
                  ? `${sector.bgColor} border-2 ${sector.borderColor} shadow-lg`
                  : 'glass-effect hover:border-white/20'
              }`}
            >
              <sector.icon className={`w-8 h-8 mx-auto mb-3 ${sector.color}`} />
              <div className="text-white font-semibold mb-1">{sector.name}</div>
              <div className={`text-sm ${sector.color} font-mono`}>{sector.model}</div>
            </motion.button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Form Section */}
          <motion.div
            key={activeSector}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-effect rounded-xl p-8"
          >
            <h2 className="text-2xl font-bold text-white mb-6">
              {sectors.find(s => s.id === activeSector)?.name} Fraud Detection
            </h2>

            <Suspense fallback={<div className="flex items-center justify-center p-12"><Loader className="w-8 h-8 animate-spin text-sapphire-400" /></div>}>
              {activeSector === 'banking' && (
                <BankingForm onResult={handleResult} onLoading={handleLoading} />
              )}
              {activeSector === 'medical' && (
                <MedicalForm onResult={handleResult} onLoading={handleLoading} />
              )}
              {activeSector === 'ecommerce' && (
                <EcommerceForm onResult={handleResult} onLoading={handleLoading} />
              )}
              {activeSector === 'supply_chain' && (
                <SupplyChainForm onResult={handleResult} onLoading={handleLoading} />
              )}
            </Suspense>
          </motion.div>

          {/* Results Section */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-effect rounded-xl p-8"
          >
            <h2 className="text-2xl font-bold text-white mb-6">Analysis Results</h2>

            <AnimatePresence mode="wait">
              {loading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center p-12"
                >
                  <Loader className="w-16 h-16 animate-spin text-sapphire-400 mb-4" />
                  <p className="text-gray-300">Analyzing fraud patterns...</p>
                  <p className="text-gray-500 text-sm mt-2">This may take a few seconds</p>
                </motion.div>
              ) : result ? (
                <ResultDisplay result={result} onReset={handleReset} />
              ) : (
                <motion.div
                  key="empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex flex-col items-center justify-center p-12 text-center"
                >
                  <div className="w-24 h-24 rounded-full bg-sapphire-500/20 flex items-center justify-center mb-4">
                    <Shield className="w-12 h-12 text-sapphire-400" />
                  </div>
                  <p className="text-gray-300 mb-2">No analysis yet</p>
                  <p className="text-gray-500 text-sm">Fill out the form and submit to see fraud detection results</p>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </div>

        {/* Info Section */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="mt-12 glass-effect rounded-xl p-8"
        >
          <h3 className="text-xl font-bold text-white mb-4">How This Works</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 text-sm">
            <div>
              <div className="text-sapphire-400 font-semibold mb-2">1. Submit Data</div>
              <p className="text-gray-400">Enter transaction, claim, or activity details in the form above</p>
            </div>
            <div>
              <div className="text-purple-400 font-semibold mb-2">2. AI Analysis</div>
              <p className="text-gray-400">LangGraph routes to sector-specific LLM with RAG context</p>
            </div>
            <div>
              <div className="text-sapphire-400 font-semibold mb-2">3. Fraud Score</div>
              <p className="text-gray-400">Receive 0-100% fraud probability with risk level</p>
            </div>
            <div>
              <div className="text-yellow-400 font-semibold mb-2">4. Explanation</div>
              <p className="text-gray-400">Get human-readable reasoning for the fraud assessment</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function Shield({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  )
}

