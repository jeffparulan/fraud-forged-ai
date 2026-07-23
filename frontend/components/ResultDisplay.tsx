'use client'

import { motion } from 'framer-motion'
import { FraudDetectionResponse } from '@/lib/api'
import {
  AlertTriangle, CheckCircle, XCircle, Info, Clock, Cpu, RefreshCw,
  GitBranch, ShieldAlert, CircleDot,
} from 'lucide-react'

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
          <div className="text-sm font-semibold text-white leading-snug">
            {/MedGemma/i.test(result.model_used || '') ? (
              <span className="inline-flex items-center flex-wrap gap-x-1 gap-y-1">
                <img src="/gcp-logo.png" alt="Google Cloud Platform" className="inline-block w-3.5 h-3.5 shrink-0" />
                <span>{result.model_used}</span>
                {/Nemotron/i.test(result.model_used || '') && (
                  <img src="/nvidia-logo.svg" alt="NVIDIA" className="inline-block w-3.5 h-3.5 shrink-0" />
                )}
              </span>
            ) : /Nemotron/i.test(result.model_used || '') ? (
              <span className="inline-flex items-center flex-wrap gap-x-1">
                <img src="/nvidia-logo.svg" alt="NVIDIA" className="inline-block w-3.5 h-3.5 shrink-0" />
                <span>{result.model_used}</span>
              </span>
            ) : /Qwen/i.test(result.model_used || '') ? (
              <span className="inline-flex items-center flex-wrap gap-x-1">
                <img src="/qwen-logo.svg" alt="Qwen" className="inline-block w-3.5 h-3.5 shrink-0" />
                <span>{result.model_used}</span>
              </span>
            ) : (
              result.model_used
            )}
          </div>
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

      {/* Score contribution breakdown — rule signals that moved the score */}
      {result.score_breakdown && result.score_breakdown.length > 0 && (
        <div className="bg-nightfall-900/50 rounded-lg p-4">
          <div className="text-sm font-semibold text-sapphire-400 mb-3">Score Contributions</div>
          <ul className="space-y-1.5">
            {result.score_breakdown.map((item, i) => {
              const positive = item.points > 0
              const neutral = item.points === 0
              const label = item.label || (item as { reason?: string }).reason || item.signal || 'Signal'
              return (
                <li key={i} className="flex items-start justify-between text-sm gap-3">
                  <span className="text-gray-300 flex-1 min-w-0">{label}</span>
                  <span
                    className={
                      neutral
                        ? 'text-yellow-400 font-mono text-xs shrink-0'
                        : positive
                          ? 'text-red-400 font-mono shrink-0'
                          : 'text-green-400 font-mono shrink-0'
                    }
                  >
                    {neutral ? '—' : `${item.points > 0 ? '+' : ''}${item.points}`}
                  </span>
                </li>
              )
            })}
          </ul>
          <p className="mt-3 text-[11px] text-gray-500 leading-relaxed">
            Each row is a deterministic billing/risk signal. Positive points raise fraud risk;
            negative points lower it. Final verdict also incorporates clinical Stage 1 and RAG.
          </p>
        </div>
      )}

      {/* Risk Factors */}
      {result.risk_factors && result.risk_factors.length > 0 && (
        <div className="bg-nightfall-900/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <ShieldAlert className="w-4 h-4 text-orange-400" />
            <div className="text-sm font-semibold text-orange-400">Risk Factors Identified</div>
          </div>
          <ul className="space-y-2">
            {result.risk_factors.map((factor, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                <CircleDot className="w-3.5 h-3.5 mt-0.5 text-orange-400/70 shrink-0" />
                {factor}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Decision Trace: shows how the LangGraph pipeline reached this verdict */}
      {result.decision_trace && result.decision_trace.length > 0 && (
        <div className="bg-nightfall-900/50 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <GitBranch className="w-4 h-4 text-sapphire-400" />
            <div className="text-sm font-semibold text-sapphire-400">Pipeline Decision Trace</div>
          </div>
          {result.pipeline_meta && (
            <div className="mb-3 flex flex-wrap gap-2 text-[11px] text-gray-400">
              {result.pipeline_meta.analysis_method && (
                <span className="px-2 py-0.5 rounded bg-nightfall-800 border border-nightfall-700">
                  method: {result.pipeline_meta.analysis_method}
                </span>
              )}
              {result.pipeline_meta.mcp_status && (
                <span className="px-2 py-0.5 rounded bg-nightfall-800 border border-nightfall-700">
                  mcp: {result.pipeline_meta.mcp_status}
                </span>
              )}
              {typeof result.pipeline_meta.rag_top_score === 'number' && (
                <span className="px-2 py-0.5 rounded bg-nightfall-800 border border-nightfall-700">
                  rag top: {result.pipeline_meta.rag_top_score.toFixed(3)}
                </span>
              )}
              {result.pipeline_meta.embedding_source && (
                <span className="px-2 py-0.5 rounded bg-nightfall-800 border border-nightfall-700">
                  embed: {result.pipeline_meta.embedding_source}
                </span>
              )}
              {result.pipeline_meta.guardrail_adjusted && (
                <span className="px-2 py-0.5 rounded bg-yellow-500/20 border border-yellow-500/40 text-yellow-300">
                  guardrail escalated
                </span>
              )}
            </div>
          )}
          <ol className="relative space-y-4 pl-1">
            {result.decision_trace.map((step, i) => {
              const stepColor =
                step.status === 'fallback' ? 'text-yellow-400 border-yellow-400/50'
                : step.status === 'empty' ? 'text-gray-500 border-gray-500/50'
                : 'text-green-400 border-green-400/50'
              return (
                <li key={i} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-bold ${stepColor}`}>
                      {i + 1}
                    </div>
                    {i < result.decision_trace!.length - 1 && (
                      <div className="w-px flex-1 bg-nightfall-700 mt-1" />
                    )}
                  </div>
                  <div className="pb-1">
                    <div className="text-sm font-medium text-white flex items-center gap-2">
                      {step.title}
                      {typeof step.latency_ms === 'number' && (
                        <span className="text-[10px] text-gray-500 font-normal">{step.latency_ms}ms</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-400 leading-relaxed">{step.detail}</div>
                  </div>
                </li>
              )
            })}
          </ol>
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

