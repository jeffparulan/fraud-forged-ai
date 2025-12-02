/**
 * Runtime configuration API route
 * 
 * This allows the frontend to fetch the backend URL at runtime,
 * ensuring it's always correct even if environment variables change.
 */

import { NextResponse } from 'next/server'

export async function GET() {
  // Get backend URL from environment variable (set at build/deploy time)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                 process.env.BACKEND_URL || 
                 'http://localhost:8000'

  return NextResponse.json({
    apiUrl,
    timestamp: new Date().toISOString(),
  })
}

