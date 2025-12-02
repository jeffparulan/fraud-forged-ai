'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { detectFraud, FraudDetectionResponse } from '@/lib/api'
import { AlertCircle } from 'lucide-react'
import { validateNumber, validateIPAddress, validateWalletAddress, validateCountry } from '@/lib/validation'

interface Props {
  onResult: (result: FraudDetectionResponse) => void
  onLoading: (loading: boolean) => void
}

const SAMPLE_SCENARIOS = [
  {
    name: 'Legitimate Wire Transfer',
    data: {
      transaction_id: 'TXN-2024-98765',
      amount: '250.00',
      transaction_type: 'wire_transfer',
      source_country: 'United States',
      destination_country: 'United States',
      transaction_time: '14:30',
      account_age_days: '1825',
      kyc_verified: true,
      transaction_velocity: '2',
      ip_address: '192.168.1.100',
      previous_flagged: false,
      sender_wallet: '',
      receiver_wallet: ''
    }
  },
  {
    name: 'Crypto Rug Pull (High Risk)',
    data: {
      transaction_id: 'TXN-2024-45821',
      amount: '500000.00',
      transaction_type: 'crypto_withdrawal',
      source_country: 'Cayman Islands',
      destination_country: 'Unknown',
      transaction_time: '03:15',
      account_age_days: '3',
      kyc_verified: false,
      transaction_velocity: '25',
      ip_address: 'TOR Network',
      previous_flagged: true,
      sender_wallet: '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbb',
      receiver_wallet: '0x0000000000000000000000000000000000000000'
    }
  },
  {
    name: 'Crypto Mixer Laundering (Critical Risk)',
    data: {
      transaction_id: 'TXN-2024-88932',
      amount: '2500000.00',
      transaction_type: 'crypto_transfer',
      source_country: 'Russia',
      destination_country: 'Unknown',
      transaction_time: '02:45',
      account_age_days: '1',
      kyc_verified: false,
      transaction_velocity: '45',
      ip_address: 'TOR Network',
      previous_flagged: true,
      sender_wallet: '0xD4c7f8E19ab6d6e6f3e2C7B8F9dA1c2E3f4A5b6C',
      receiver_wallet: '0x1234567890abcdef1234567890abcdef12345678'
    }
  },
  {
    name: 'NFT Wash Trading (High Risk)',
    data: {
      transaction_id: 'TXN-2024-77234',
      amount: '850000.00',
      transaction_type: 'nft_purchase',
      source_country: 'United States',
      destination_country: 'United States',
      transaction_time: '04:20',
      account_age_days: '7',
      kyc_verified: false,
      transaction_velocity: '18',
      ip_address: '45.33.32.156',
      previous_flagged: false,
      sender_wallet: '0xA1b2C3d4E5f6789012345678901234567890AbCd',
      receiver_wallet: '0xDeF123456789aBcDeF1234567890AbCdEf123456'
    }
  },
  {
    name: 'Money Laundering Pattern (High Risk)',
    data: {
      transaction_id: 'TXN-2024-33219',
      amount: '9900.00',
      transaction_type: 'wire_transfer',
      source_country: 'Nigeria',
      destination_country: 'Switzerland',
      transaction_time: '23:45',
      account_age_days: '45',
      kyc_verified: true,
      transaction_velocity: '12',
      ip_address: 'VPN Detected',
      previous_flagged: false,
      sender_wallet: '',
      receiver_wallet: ''
    }
  },
  {
    name: 'Crypto Structuring Pattern (Medium Risk)',
    data: {
      transaction_id: 'TXN-2024-44567',
      amount: '4800.00',
      transaction_type: 'crypto_transfer',
      source_country: 'United States',
      destination_country: 'United States',
      transaction_time: '16:30',
      account_age_days: '120',
      kyc_verified: false,
      transaction_velocity: '8',
      ip_address: '192.168.1.200',
      previous_flagged: false,
      sender_wallet: '0x8ba1f109551bD432803012645aBc136c22C1779b',
      receiver_wallet: '0xAb8483F64d9C6d1EcF9b849Ae677dD3315835cb2'
    }
  }
]

const COUNTRIES = [
  'United States', 'United Kingdom', 'Canada', 'Germany', 'France', 'Japan',
  'Switzerland', 'Singapore', 'Australia', 'Netherlands', 'Hong Kong',
  'Cayman Islands', 'British Virgin Islands', 'Nigeria', 'Russia', 'China',
  'Unknown'
]

export default function BankingForm({ onResult, onLoading }: Props) {
  const [formData, setFormData] = useState({
    transaction_id: '',
    amount: '',
    transaction_type: 'wire_transfer',
    source_country: 'United States',
    destination_country: 'United States',
    transaction_time: '',
    account_age_days: '',
    kyc_verified: true,
    transaction_velocity: '',
    ip_address: '',
    previous_flagged: false,
    sender_wallet: '',
    receiver_wallet: ''
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    // Client-side validation (OWASP A03: Injection prevention)
    if (!validateNumber(formData.amount, 0, 100000000)) {
      setError('Invalid transaction amount. Please enter a valid number between 0 and 100,000,000.')
      return
    }
    
    if (formData.ip_address && !validateIPAddress(formData.ip_address)) {
      setError('Invalid IP address format. Use a valid IP or descriptive text like "VPN Detected".')
      return
    }
    
    // Validate wallet addresses (only if non-empty after trimming)
    const senderWallet = formData.sender_wallet?.trim() || ''
    if (senderWallet && !validateWalletAddress(senderWallet)) {
      setError('Invalid sender wallet address format. Must be a valid Ethereum address (0x...).')
      return
    }
    
    const receiverWallet = formData.receiver_wallet?.trim() || ''
    if (receiverWallet && !validateWalletAddress(receiverWallet)) {
      setError('Invalid receiver wallet address format. Must be a valid Ethereum address (0x...).')
      return
    }
    
    if (!validateCountry(formData.source_country)) {
      setError('Invalid source country format.')
      return
    }
    
    if (!validateCountry(formData.destination_country)) {
      setError('Invalid destination country format.')
      return
    }
    
    setIsLoading(true)
    onLoading(true)

    try {
      const result = await detectFraud({
        sector: 'banking',
        data: {
          transaction_id: formData.transaction_id,
          amount: parseFloat(formData.amount),
          transaction_type: formData.transaction_type,
          location: formData.source_country,
          source_country: formData.source_country,
          destination_country: formData.destination_country,
          time: formData.transaction_time,
          account_age_days: parseInt(formData.account_age_days),
          kyc_verified: formData.kyc_verified,
          transaction_velocity: parseInt(formData.transaction_velocity),
          ip_address: formData.ip_address,
          previous_flagged: formData.previous_flagged,
          sender_wallet: senderWallet,
          receiver_wallet: receiverWallet
        }
      })
      onResult(result)
      setIsLoading(false)
    } catch (err: any) {
      setError(err.message || 'Failed to detect fraud')
      setIsLoading(false)
      onLoading(false)
    }
  }

  const loadSample = (index: number) => {
    const sample = SAMPLE_SCENARIOS[index]
    setFormData(sample.data)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Sample Scenario Buttons */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Load Sample Scenario:
        </label>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {SAMPLE_SCENARIOS.map((scenario, index) => (
            <button
              key={index}
              type="button"
              onClick={() => loadSample(index)}
              className="px-3 py-2 text-xs glass-effect text-white rounded hover:bg-white/10 transition-colors text-left"
            >
              {scenario.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Transaction ID
          </label>
          <input
            type="text"
            required
            value={formData.transaction_id}
            onChange={(e) => setFormData({ ...formData, transaction_id: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="TXN-2024-00001"
            aria-label="Transaction ID"
            maxLength={50}
            autoComplete="off"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Transaction Amount ($)
          </label>
          <input
            type="number"
            step="0.01"
            required
            min="0"
            max="100000000"
            value={formData.amount}
            onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="10000.00"
            aria-label="Transaction Amount in USD"
            aria-required="true"
          />
        </div>
      </div>

      {/* Crypto Wallet Addresses (for crypto transactions) */}
      {(formData.transaction_type.includes('crypto') || formData.transaction_type === 'nft_purchase') && (
        <div className="grid grid-cols-2 gap-4 p-4 bg-sapphire-500/10 border border-sapphire-500/30 rounded-lg">
          <div>
            <label className="block text-sm font-medium text-sapphire-300 mb-2 flex items-center gap-2">
              <span>🔗</span> Sender Wallet Address
            </label>
            <input
              type="text"
              value={formData.sender_wallet}
              onChange={(e) => setFormData({ ...formData, sender_wallet: e.target.value })}
              className="w-full px-4 py-3 bg-nightfall-900 border border-sapphire-500/30 rounded-lg text-white focus:border-sapphire-500 focus:outline-none font-mono text-sm"
              placeholder="0xabc...def"
            />
            <p className="text-xs text-gray-400 mt-1">Verify on Etherscan for traceability</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-sapphire-300 mb-2 flex items-center gap-2">
              <span>🔗</span> Receiver Wallet Address
            </label>
            <input
              type="text"
              value={formData.receiver_wallet}
              onChange={(e) => setFormData({ ...formData, receiver_wallet: e.target.value })}
              className="w-full px-4 py-3 bg-nightfall-900 border border-sapphire-500/30 rounded-lg text-white focus:border-sapphire-500 focus:outline-none font-mono text-sm"
              placeholder="0x123...xyz"
            />
            <p className="text-xs text-gray-400 mt-1">Check for known fraud addresses</p>
          </div>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Transaction Type
        </label>
        <select
          value={formData.transaction_type}
          onChange={(e) => setFormData({ ...formData, transaction_type: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
        >
          <option value="wire_transfer">Wire Transfer</option>
          <option value="crypto_withdrawal">Crypto Withdrawal</option>
          <option value="crypto_deposit">Crypto Deposit</option>
          <option value="crypto_transfer">Crypto Transfer</option>
          <option value="nft_purchase">NFT Purchase</option>
          <option value="ach_transfer">ACH Transfer</option>
          <option value="international_wire">International Wire</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Source Country
          </label>
          <select
            value={formData.source_country}
            onChange={(e) => setFormData({ ...formData, source_country: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          >
            {COUNTRIES.map(country => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Destination Country
          </label>
          <select
            value={formData.destination_country}
            onChange={(e) => setFormData({ ...formData, destination_country: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          >
            {COUNTRIES.map(country => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Transaction Time (24h)
          </label>
          <input
            type="text"
            required
            value={formData.transaction_time}
            onChange={(e) => setFormData({ ...formData, transaction_time: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="14:30"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Account Age (days)
          </label>
          <input
            type="number"
            required
            value={formData.account_age_days}
            onChange={(e) => setFormData({ ...formData, account_age_days: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="365"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Velocity (24h txns)
          </label>
          <input
            type="number"
            required
            value={formData.transaction_velocity}
            onChange={(e) => setFormData({ ...formData, transaction_velocity: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="5"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          IP Address / Network
        </label>
        <input
          type="text"
          required
          value={formData.ip_address}
          onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., 192.168.1.1, VPN Detected, TOR Network"
        />
      </div>

      <div className="flex gap-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.kyc_verified}
            onChange={(e) => setFormData({ ...formData, kyc_verified: e.target.checked })}
            className="w-5 h-5 rounded border-white/10 bg-nightfall-900 text-sapphire-500 focus:ring-sapphire-500"
          />
          <span className="text-gray-300">KYC Verified</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.previous_flagged}
            onChange={(e) => setFormData({ ...formData, previous_flagged: e.target.checked })}
            className="w-5 h-5 rounded border-white/10 bg-nightfall-900 text-sapphire-500 focus:ring-sapphire-500"
          />
          <span className="text-gray-300">Previously Flagged</span>
        </label>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400"
        >
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </motion.div>
      )}

      <motion.button
        type="submit"
        disabled={isLoading}
        whileHover={!isLoading ? { scale: 1.02 } : {}}
        whileTap={!isLoading ? { scale: 0.98 } : {}}
        className={`w-full px-6 py-3 bg-gradient-to-r from-sapphire-600 to-blue-600 text-white rounded-lg font-semibold transition-opacity ${
          isLoading ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {isLoading ? 'Analyzing...' : 'Analyze Transaction'}
      </motion.button>
    </form>
  )
}
