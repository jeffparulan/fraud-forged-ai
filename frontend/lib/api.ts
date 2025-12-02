import axios from 'axios'
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

// Create axios instance with security defaults
const apiClient = axios.create({
  timeout: 120000, // 120s to accommodate slow OpenRouter free tier (backend has 90s timeout)
  headers: {
    'Content-Type': 'application/json',
  },
  // Prevent axios from automatically parsing responses that could contain XSS
  transformResponse: [(data) => {
    try {
      return JSON.parse(data)
    } catch (e) {
      throw new Error('Invalid response format')
    }
  }]
})

// Request interceptor for security
apiClient.interceptors.request.use(
  (config) => {
    // Rate limiting check (client-side)
    if (!checkRateLimit()) {
      throw new Error('Too many requests. Please wait a moment and try again.')
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't expose internal error details
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      if (status === 401) {
        throw new Error('Authentication required')
      } else if (status === 403) {
        throw new Error('Access forbidden')
      } else if (status === 429) {
        throw new Error('Too many requests. Please try again later.')
      } else if (status === 500) {
        throw new Error('Server error. Please try again later.')
      } else if (status === 503) {
        throw new Error('Service temporarily unavailable')
      }
    }
    throw error
  }
)

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
    const response = await apiClient.post<FraudDetectionResponse>(url, {
      sector: request.sector,
      data: sanitizedData
    })
    
    // Validate response structure
    if (!response.data || typeof response.data.fraud_score !== 'number') {
      throw new Error('Invalid response format')
    }
    
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message || 'Fraud detection failed'
      throw new Error(message)
    }
    throw error
  }
}

export const checkHealth = async () => {
  try {
    const apiUrl = getApiUrl()
    const response = await axios.get(`${apiUrl}/api/health`)
    return response.data
  } catch (error) {
    throw new Error('Backend service unavailable')
  }
}

export const getModels = async () => {
  try {
    const apiUrl = getApiUrl()
    const response = await axios.get(`${apiUrl}/api/models`)
    return response.data
  } catch (error) {
    throw new Error('Failed to fetch models')
  }
}

