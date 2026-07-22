/**
 * Runtime configuration API route.
 * Derives the sibling Cloud Run backend URL from the Host header when possible
 * so the LinkedIn/resume frontend URL always pairs with the matching backend.
 */

import { NextRequest, NextResponse } from 'next/server'
import { backendFromFrontendHost } from '@/lib/config'

export async function GET(request: NextRequest) {
  const host = request.headers.get('host') || ''
  const derived = backendFromFrontendHost(host.split(':')[0])

  const apiUrl =
    derived ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    'http://localhost:8000'

  return NextResponse.json({
    apiUrl,
    timestamp: new Date().toISOString(),
  })
}
