'use client'

import Link from 'next/link'
import { Github, Linkedin, ExternalLink } from 'lucide-react'
import Logo from './Logo'

export default function Footer() {
  return (
    <footer className="glass-effect border-t border-white/10 mt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="col-span-1 md:col-span-2">
            <div className="mb-4">
              <Logo size={32} showText={true} />
            </div>
            <p className="text-gray-400 mb-4">
              FraudForgeAI: Simplified GenAI Workflows | Robust AI Guards | Near-Zero Cost Open-Source. Beat BPM Bloat—for Pennies.
            </p>
            <div className="flex gap-4">
              <a
                href="https://github.com/jeffparulan/fraud-forged-ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-white transition-colors"
              >
                <Github className="w-6 h-6" />
              </a>
              <a
                href="https://www.linkedin.com/in/jeff-parulan/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-400 hover:text-white transition-colors"
                aria-label="Jeff Parulan's LinkedIn profile"
              >
                <Linkedin className="w-6 h-6" />
              </a>
            </div>
          </div>

          {/* Navigation */}
          <div>
            <h3 className="text-white font-semibold mb-4">Platform</h3>
            <ul className="space-y-2">
              <li>
                <Link href="/use-cases" className="text-gray-400 hover:text-white transition-colors">
                  Use Cases
                </Link>
              </li>
              <li>
                <Link href="/architecture" className="text-gray-400 hover:text-white transition-colors">
                  Architecture
                </Link>
              </li>
              <li>
                <Link href="/features" className="text-gray-400 hover:text-white transition-colors">
                  Features
                </Link>
              </li>
              <li>
                <Link href="/how-it-works" className="text-gray-400 hover:text-white transition-colors">
                  How It Works
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h3 className="text-white font-semibold mb-4">Resources</h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="https://github.com/jeffparulan/fraud-forged-ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-white transition-colors flex items-center gap-1"
                >
                  GitHub
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="/docs/fraud-diagram.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-400 hover:text-white transition-colors flex items-center gap-1"
                >
                  Architecture Diagram
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <Link href="/detect" className="text-gray-400 hover:text-white transition-colors">
                  Live Demo
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/10 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
          <p className="text-gray-400 text-sm">
            © 2025 FraudForge AI. Open source under MIT License.
          </p>
          <p className="text-gray-400 text-sm mt-4 md:mt-0">
            Built with ❤️ using GenAI • LangGraph • Vertex AI • Hugging Face • Pinecone • MCP
          </p>
        </div>
      </div>
    </footer>
  )
}

