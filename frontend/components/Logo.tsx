'use client'

import Image from 'next/image'
import { motion } from 'framer-motion'
import { useState, useEffect } from 'react'

interface LogoProps {
  size?: number
  className?: string
  showText?: boolean
  animated?: boolean
}

export default function Logo({ size = 32, className = '', showText = true, animated = false }: LogoProps) {
  // Directly use PNG, fallback to SVG if PNG doesn't exist
  const logoSrc = '/logo.png'
  
  const logoContent = (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <Image
          src={logoSrc}
          alt="FraudForge AI Logo"
          width={size}
          height={size}
          className="drop-shadow-lg"
          priority
          onError={(e) => {
            // Fallback to SVG if PNG doesn't exist
            const target = e.target as HTMLImageElement
            if (target.src !== `${window.location.origin}/logo.svg`) {
              target.src = '/logo.svg'
            }
          }}
        />
      </div>
      {showText && (
        <span className="text-xl font-bold text-white">FraudForge AI</span>
      )}
    </div>
  )

  if (animated) {
    return (
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3 }}
      >
        {logoContent}
      </motion.div>
    )
  }

  return logoContent
}

