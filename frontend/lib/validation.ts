/**
 * Input validation and sanitization utilities
 * OWASP Top 10 protection: A03:2021 – Injection
 */

// Sanitize string input to prevent XSS
export function sanitizeString(input: string): string {
  if (typeof input !== 'string') {
    return ''
  }
  
  // Remove potentially dangerous characters and protocols
  return input
    .replace(/[<>"'`\\]/g, '') // Remove <, >, ", ', `, \
    .replace(/[\x00-\x1F\x7F]/g, '') // Remove control characters
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/data:/gi, '') // Remove data: protocol
    .replace(/vbscript:/gi, '') // Remove vbscript: protocol
    .replace(/file:/gi, '') // Remove file: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .trim()
    .slice(0, 10000) // Max length limit
}

// Validate email format
export function validateEmail(email: string): boolean {
  if (!email || typeof email !== 'string') return false
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email) && email.length <= 254
}

// Validate numeric input
export function validateNumber(value: any, min?: number, max?: number): boolean {
  const num = typeof value === 'string' ? parseFloat(value) : Number(value)
  if (isNaN(num)) return false
  if (min !== undefined && num < min) return false
  if (max !== undefined && num > max) return false
  return true
}

// Validate IP address format
export function validateIPAddress(ip: string): boolean {
  if (!ip || typeof ip !== 'string') return false
  // Allow common patterns like "VPN Detected", "TOR Network", etc.
  if (/^(VPN|TOR|Proxy|Unknown|Detected)/i.test(ip)) return true
  // Validate IPv4
  const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/
  if (ipv4Regex.test(ip)) {
    const parts = ip.split('.').map(Number)
    return parts.every(part => part >= 0 && part <= 255)
  }
  // Validate IPv6 (basic)
  const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/
  return ipv6Regex.test(ip)
}

// Validate wallet address (Ethereum format)
export function validateWalletAddress(address: string): boolean {
  // Allow empty/null/undefined (optional field)
  if (!address || typeof address !== 'string') return true
  
  // Trim whitespace
  const trimmed = address.trim()
  
  // Allow empty string after trimming
  if (trimmed === '') return true
  
  // Ethereum address: 0x followed by exactly 40 hex characters (case-insensitive)
  // Must start with 0x and be exactly 42 characters total (0x + 40 hex)
  return /^0x[a-fA-F0-9]{40}$/i.test(trimmed)
}

// Validate country name
export function validateCountry(country: string): boolean {
  if (!country || typeof country !== 'string') return false
  // Allow common country names, max 100 chars
  return country.length <= 100 && /^[a-zA-Z\s\-']+$/.test(country)
}

// Sanitize and validate form data
export function sanitizeFormData(data: Record<string, any>): Record<string, any> {
  const sanitized: Record<string, any> = {}
  
  for (const [key, value] of Object.entries(data)) {
    if (value === null || value === undefined) {
      continue
    }
    
    if (typeof value === 'string') {
      sanitized[key] = sanitizeString(value)
    } else if (typeof value === 'number') {
      // Validate number is finite
      sanitized[key] = isFinite(value) ? value : 0
    } else if (typeof value === 'boolean') {
      sanitized[key] = value
    } else if (Array.isArray(value)) {
      sanitized[key] = value.map(item => 
        typeof item === 'string' ? sanitizeString(item) : item
      )
    } else {
      sanitized[key] = value
    }
  }
  
  return sanitized
}

// Rate limiting helper (client-side check)
let requestCount = 0
let requestWindow = Date.now()
const MAX_REQUESTS = 10
const WINDOW_MS = 60000 // 1 minute

export function checkRateLimit(): boolean {
  const now = Date.now()
  
  if (now - requestWindow > WINDOW_MS) {
    requestCount = 0
    requestWindow = now
  }
  
  if (requestCount >= MAX_REQUESTS) {
    return false
  }
  
  requestCount++
  return true
}

