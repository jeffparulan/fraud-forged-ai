import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Navigation from '@/components/Navigation'
import Footer from '@/components/Footer'
import ConfigLoader from '@/components/ConfigLoader'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'),
  title: 'FraudForge AI - Simplified GenAI Fraud Detection',
  description: 'FraudForgeAI: Simplified GenAI Workflows | Robust AI Guards | Near-Zero Cost Open-Source. Beat BPM Bloat—for Pennies.',
  keywords: 'fraud detection, GenAI, machine learning, fintech, healthcare, ecommerce, supply chain',
  icons: {
    icon: [
      { url: '/favicon.png', type: 'image/png' },
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico' },
    ],
  },
  robots: {
    index: true,
    follow: true,
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    siteName: 'FraudForge AI',
    title: 'FraudForge AI - Simplified GenAI Fraud Detection',
    description: 'FraudForgeAI: Simplified GenAI Workflows | Robust AI Guards | Near-Zero Cost Open-Source. Beat BPM Bloat—for Pennies.',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FraudForge AI - Simplified GenAI Fraud Detection',
    description: 'FraudForgeAI: Simplified GenAI Workflows | Robust AI Guards | Near-Zero Cost Open-Source. Beat BPM Bloat—for Pennies.',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <ErrorBoundary>
          <ConfigLoader />
          <Navigation />
          <main className="min-h-screen" role="main">
            {children}
          </main>
          <Footer />
        </ErrorBoundary>
      </body>
    </html>
  )
}

