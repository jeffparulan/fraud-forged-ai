import { getApiUrlCached } from './config'
import { sanitizeFormData, checkRateLimit } from './validation'

// Get API URL dynamically (called on each request, not at module load)
function getApiUrl(): string {
  return getApiUrlCached()
}

export interface FraudDetectionRequest {
  sector: 'banking' | 'medical' | 'ecommerce' | 'supply_chain'
  data: Record<string, any>
}

export interface FraudDetectionResponse {
  fraud_score: number
  risk_level: string
  explanation: string
  model_used: string
  processing_time_ms: number
  similar_patterns?: number
}

function mapHttpError(status: number, fallback: string): Error {
  if (status === 401) return new Error('Authentication required')
  if (status === 403) return new Error('Access forbidden')
  if (status === 429) return new Error('Too many requests. Please try again later.')
  if (status === 500) return new Error('Server error. Please try again later.')
  if (status === 503) return new Error('Service temporarily unavailable')
  return new Error(fallback)
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 120000) // 120s

  try {
    const response = await fetch(url, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      let detail = 'Request failed'
      try {
        const errBody = await response.json()
        detail = errBody?.detail || detail
      } catch {
        // Ignore parse errors and use default detail
      }
      throw mapHttpError(response.status, detail)
    }

    try {
      return (await response.json()) as T
    } catch {
      throw new Error('Invalid response format')
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.')
    }
    throw error instanceof Error ? error : new Error('Request failed')
  } finally {
    clearTimeout(timeout)
  }
}

export const detectFraud = async (request: FraudDetectionRequest): Promise<FraudDetectionResponse> => {
  // Validate sector
  const validSectors = ['banking', 'medical', 'ecommerce', 'supply_chain']
  if (!validSectors.includes(request.sector)) {
    throw new Error('Invalid sector specified')
  }
  
  // Sanitize input data (OWASP A03: Injection prevention)
  const sanitizedData = sanitizeFormData(request.data)
  
  const apiUrl = getApiUrl()
  const url = `${apiUrl}/api/detect`
  
  try {
    // Rate limiting check (client-side)
    if (!checkRateLimit()) {
      throw new Error('Too many requests. Please wait a moment and try again.')
    }

    const data = await fetchJson<FraudDetectionResponse>(url, {
      method: 'POST',
      body: JSON.stringify({
      sector: request.sector,
      data: sanitizedData
      }),
    })
    
    // Validate response structure
    if (!data || typeof data.fraud_score !== 'number') {
      throw new Error('Invalid response format')
    }
    
    return data
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(error.message || 'Fraud detection failed')
    }
    throw new Error('Fraud detection failed')
  }
}

export const checkHealth = async () => {
  try {
    const apiUrl = getApiUrl()
    return await fetchJson(`${apiUrl}/api/health`)
  } catch {
    throw new Error('Backend service unavailable')
  }
}

export const getModels = async () => {
  try {
    const apiUrl = getApiUrl()
    return await fetchJson(`${apiUrl}/api/models`)
  } catch {
    throw new Error('Failed to fetch models')
  }
}

