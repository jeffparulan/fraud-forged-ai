/**
 * Dynamic API configuration
 * 
 * This ensures the backend URL is always correct, even if:
 * - Environment variables change
 * - Different Cloud Run revisions are deployed
 * - Different environments (dev/staging/prod)
 */

// Get API URL from multiple sources (in order of priority)
function getApiUrl(): string {
  // 1. Check if we have a runtime config (set by Next.js API route)
  if (typeof window !== 'undefined') {
    const runtimeConfig = (window as any).__APP_CONFIG__;
    if (runtimeConfig?.apiUrl) {
      return runtimeConfig.apiUrl;
    }
  }

  // 2. Check build-time environment variable (available in browser via Next.js)
  // Next.js replaces NEXT_PUBLIC_* at build time, so it's available in the browser
  if (typeof window !== 'undefined') {
    // In browser, check if it was set in the build
    const buildTimeUrl = (window as any).__NEXT_DATA__?.env?.NEXT_PUBLIC_API_URL;
    if (buildTimeUrl) {
      return buildTimeUrl;
    }
  }
  
  // Server-side or fallback: use process.env
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // 3. For local development, try to detect from window location
  if (typeof window !== 'undefined' && window.location.hostname === 'localhost') {
    return 'http://localhost:8000';
  }

  // 4. Fallback: construct from current host (for same-domain deployments)
  if (typeof window !== 'undefined') {
    // If frontend and backend are on same domain, use relative URLs
    const hostname = window.location.hostname;
    if (hostname.includes('run.app')) {
      // Cloud Run: try to construct backend URL from frontend URL
      const match = hostname.match(/fraud-forge-frontend-(\d+)\.us-central1\.run\.app/);
      if (match) {
        return `https://fraud-forge-backend-${match[1]}.us-central1.run.app`;
      }
    }
  }

  // 5. Ultimate fallback
  return 'http://localhost:8000';
}

// Cache the API URL to avoid recalculating
let cachedApiUrl: string | null = null;

export function getApiUrlCached(): string {
  if (!cachedApiUrl) {
    cachedApiUrl = getApiUrl();
    console.log('🔗 API URL configured:', cachedApiUrl);
  }
  return cachedApiUrl;
}

// Allow runtime override (useful for testing or dynamic config)
export function setApiUrl(url: string): void {
  cachedApiUrl = url;
  console.log('🔗 API URL updated to:', url);
}

// Fetch runtime config from Next.js API route (optional)
export async function loadRuntimeConfig(): Promise<void> {
  if (typeof window === 'undefined') return;

  try {
    const response = await fetch('/api/config');
    const config = await response.json();
    if (config.apiUrl) {
      (window as any).__APP_CONFIG__ = config;
      setApiUrl(config.apiUrl);
    }
  } catch (error) {
    console.warn('⚠️ Could not load runtime config, using build-time config:', error);
  }
}

