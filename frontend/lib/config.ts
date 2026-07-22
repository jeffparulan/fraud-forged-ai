/**
 * Dynamic API configuration.
 *
 * On Cloud Run the frontend is published at both URL shapes:
 *   - https://fraud-forge-frontend-<PROJECT_NUMBER>.us-central1.run.app  (canonical / LinkedIn)
 *   - https://fraud-forge-frontend-<HASH>-uc.a.run.app
 * Always map the current page host to the matching backend so CORS + API calls work
 * for whichever URL someone opens.
 */

function backendFromFrontendHost(hostname: string): string | null {
  // Project-number form (canonical resume/LinkedIn URL)
  const numbered = hostname.match(
    /^fraud-forge-frontend-(\d+)\.([a-z0-9-]+)\.run\.app$/i
  )
  if (numbered) {
    return `https://fraud-forge-backend-${numbered[1]}.${numbered[2]}.run.app`
  }

  // Hash form: fraud-forge-frontend-<hash>-uc.a.run.app
  const hashed = hostname.match(
    /^fraud-forge-frontend-([a-z0-9]+-[a-z0-9]+)\.a\.run\.app$/i
  )
  if (hashed) {
    return `https://fraud-forge-backend-${hashed[1]}.a.run.app`
  }

  return null
}

function getApiUrl(): string {
  // 1. Browser on Cloud Run → derive sibling backend from the page host first.
  //    This is what makes the LinkedIn/resume URL work without depending on build args.
  if (typeof window !== 'undefined') {
    const derived = backendFromFrontendHost(window.location.hostname)
    if (derived) return derived

    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
      return 'http://localhost:8000'
    }

    const runtimeConfig = (window as any).__APP_CONFIG__
    if (runtimeConfig?.apiUrl) return runtimeConfig.apiUrl
  }

  // 2. Build-time / server env (docker build --build-arg NEXT_PUBLIC_API_URL=...)
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  // 3. Ultimate fallback
  return 'http://localhost:8000'
}

let cachedApiUrl: string | null = null

export function getApiUrlCached(): string {
  // Re-resolve on Cloud Run so a wrong early cache can't stick to localhost
  if (typeof window !== 'undefined') {
    const derived = backendFromFrontendHost(window.location.hostname)
    if (derived) {
      cachedApiUrl = derived
      return derived
    }
  }

  if (!cachedApiUrl) {
    cachedApiUrl = getApiUrl()
  }
  return cachedApiUrl
}

export function setApiUrl(url: string): void {
  cachedApiUrl = url
}

export async function loadRuntimeConfig(): Promise<void> {
  if (typeof window === 'undefined') return

  // Prefer host-derived Cloud Run URL; only hit /api/config as a fallback.
  const derived = backendFromFrontendHost(window.location.hostname)
  if (derived) {
    ;(window as any).__APP_CONFIG__ = { apiUrl: derived }
    setApiUrl(derived)
    return
  }

  try {
    const response = await fetch('/api/config')
    const config = await response.json()
    if (config.apiUrl) {
      ;(window as any).__APP_CONFIG__ = config
      setApiUrl(config.apiUrl)
    }
  } catch (error) {
    console.warn('Could not load runtime config, using build-time config:', error)
  }
}

export { backendFromFrontendHost }
