'use client'

import { motion } from 'framer-motion'
import { FraudDetectionResponse } from '@/lib/api'
import { AlertTriangle, CheckCircle, XCircle, Info, Clock, Cpu, RefreshCw } from 'lucide-react'

interface Props {
  result: FraudDetectionResponse
  onReset: () => void
}

export default function ResultDisplay({ result, onReset }: Props) {
  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'text-red-600'  // 85-100%: Dark red for critical danger
      case 'high':
        return 'text-orange-500'  // 60-84%: Orange for high danger
      case 'medium':
        return 'text-yellow-400'  // 30-59%: Yellow for warning
      case 'low':
        return 'text-green-400'  // 0-29%: Green for safe
      default:
        return 'text-green-400'
    }
  }

  const getRiskBgColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'bg-red-600/30 border-red-600/50'  // 85-100%: Critical danger
      case 'high':
        return 'bg-orange-500/20 border-orange-500/40'  // 60-84%: High danger
      case 'medium':
        return 'bg-yellow-500/20 border-yellow-500/30'  // 30-59%: Warning
      case 'low':
        return 'bg-green-500/20 border-green-500/30'  // 0-29%: Safe
      default:
        return 'bg-green-500/20 border-green-500/30'
    }
  }

  const getRiskIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return XCircle  // 85-100%: X icon for critical
      case 'high':
        return AlertTriangle  // 60-84%: Warning triangle for high
      case 'medium':
        return AlertTriangle  // 30-59%: Warning triangle for medium
      case 'low':
        return CheckCircle  // 0-29%: Check mark for safe
      default:
        return CheckCircle
    }
  }

  const RiskIcon = getRiskIcon(result.risk_level)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Fraud Score Gauge */}
      <div className="text-center">
        <div className="relative inline-block">
          <svg className="w-40 h-40 transform -rotate-90">
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="currentColor"
              strokeWidth="10"
              fill="transparent"
              className="text-nightfall-800"
            />
            <circle
              cx="80"
              cy="80"
              r="70"
              stroke="currentColor"
              strokeWidth="10"
              fill="transparent"
              strokeDasharray={`${2 * Math.PI * 70}`}
              strokeDashoffset={`${2 * Math.PI * 70 * (1 - result.fraud_score / 100)}`}
              className={getRiskColor(result.risk_level)}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className={`text-4xl font-bold ${getRiskColor(result.risk_level)}`}>
              {result.fraud_score.toFixed(1)}%
            </div>
            <div className="text-gray-400 text-sm">Fraud Score</div>
          </div>
        </div>
      </div>

      {/* Risk Level Badge */}
      <div className={`p-4 rounded-lg border ${getRiskBgColor(result.risk_level)} flex items-center gap-3`}>
        <RiskIcon className={`w-6 h-6 ${getRiskColor(result.risk_level)}`} />
        <div className="flex-1">
          <div className="text-sm text-gray-400">Risk Level</div>
          <div className={`text-xl font-bold uppercase ${getRiskColor(result.risk_level)}`}>
            {result.risk_level}
          </div>
        </div>
      </div>

      {/* Explanation */}
      <div className="bg-nightfall-900/50 rounded-lg p-4">
        <div className="text-sm font-semibold text-sapphire-400 mb-3">AI Analysis</div>
        <div 
          className="text-gray-300 leading-relaxed min-h-[120px] max-h-[300px] overflow-y-auto px-2 py-2 text-sm"
          role="text" 
          aria-label={`AI analysis: ${result.explanation}`}
          style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}
        >
          {result.explanation}
        </div>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-nightfall-900/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-4 h-4 text-purple-400" />
            <div className="text-xs text-gray-400">Model Used</div>
          </div>
          <div className="text-sm font-semibold text-white">{result.model_used}</div>
        </div>

        <div className="bg-nightfall-900/30 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-blue-400" />
            <div className="text-xs text-gray-400">Processing Time</div>
          </div>
          <div className="text-sm font-semibold text-white">{result.processing_time_ms}ms</div>
        </div>
      </div>

      {/* Similar Patterns */}
      {result.similar_patterns !== undefined && (
        <div className="bg-nightfall-900/30 rounded-lg p-3">
          <div className="text-xs text-gray-400 mb-1">Similar Fraud Patterns Found</div>
          <div className="text-lg font-semibold text-sapphire-400">{result.similar_patterns}</div>
        </div>
      )}

      {/* Reset Button */}
      <motion.button
        onClick={onReset}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className="w-full px-6 py-3 glass-effect text-white rounded-lg font-semibold flex items-center justify-center gap-2"
      >
        <RefreshCw className="w-5 h-5" />
        Analyze Another Case
      </motion.button>
    </motion.div>
  )
}

