'use client'

import { useEffect } from 'react'
import { loadRuntimeConfig } from '@/lib/config'

/**
 * Client component that loads runtime configuration on app startup
 * This ensures the backend URL is always up-to-date
 */
export default function ConfigLoader() {
  useEffect(() => {
    // Load runtime config when app starts
    loadRuntimeConfig().catch(console.error)
  }, [])

  // This component doesn't render anything
  return null
}

