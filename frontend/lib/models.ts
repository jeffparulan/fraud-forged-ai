/**
 * Sector model labels from backend /api/models.
 * Falls back to static strings only if the API is unreachable.
 */
'use client'

import { useEffect, useState } from 'react'
import { getModels } from '@/lib/api'

export type SectorId = 'banking' | 'medical' | 'ecommerce' | 'supply_chain'

export type SectorModelSummary = {
  label: string
  pipeline: string
  primary: string
  route_display?: string
  blurb?: string
  fallbacks: string[]
}

const FALLBACK_SUMMARY: Record<SectorId, SectorModelSummary> = {
  banking: {
    label: 'Banking & Crypto',
    pipeline: 'single-stage',
    primary: 'Qwen3-32B (HF Inference)',
    blurb: 'Financial reasoning and AML detection with Qwen (Hugging Face)',
    fallbacks: [],
  },
  medical: {
    label: 'Healthcare & Medical Claims',
    pipeline: 'two-stage',
    primary: 'Two-Stage: MedGemma-27B → Qwen3-32B',
    blurb: 'MedGemma clinical validation, then Qwen fraud pattern analysis',
    fallbacks: [],
  },
  ecommerce: {
    label: 'E-commerce & Marketplace',
    pipeline: 'single-stage',
    primary: 'Nemotron-Ultra-550B (OpenRouter)',
    blurb: 'Marketplace fraud and refund-abuse detection with NVIDIA Nemotron',
    fallbacks: [],
  },
  supply_chain: {
    label: 'Supply Chain & Logistics',
    pipeline: 'single-stage',
    primary: 'Nemotron-Ultra-550B (OpenRouter)',
    blurb: 'Supplier and logistics fraud detection with NVIDIA Nemotron',
    fallbacks: [],
  },
}

let cachedSummary: Record<string, SectorModelSummary> | null = null
let inflight: Promise<Record<string, SectorModelSummary>> | null = null

export async function loadModelSummary(): Promise<Record<string, SectorModelSummary>> {
  if (cachedSummary) return cachedSummary
  if (!inflight) {
    inflight = getModels()
      .then((data: any) => {
        const summary = (data?.summary || {}) as Record<string, SectorModelSummary>
        cachedSummary = { ...FALLBACK_SUMMARY, ...summary }
        return cachedSummary
      })
      .catch(() => {
        cachedSummary = FALLBACK_SUMMARY
        return cachedSummary
      })
      .finally(() => {
        inflight = null
      })
  }
  return inflight
}

export function useModelSummary() {
  const [summary, setSummary] = useState<Record<string, SectorModelSummary>>(
    cachedSummary || FALLBACK_SUMMARY
  )
  const [loading, setLoading] = useState(!cachedSummary)

  useEffect(() => {
    let cancelled = false
    loadModelSummary().then((s) => {
      if (!cancelled) {
        setSummary(s)
        setLoading(false)
      }
    })
    return () => {
      cancelled = true
    }
  }, [])

  return { summary, loading, getPrimary: (sector: SectorId) => summary[sector]?.primary || FALLBACK_SUMMARY[sector].primary }
}
