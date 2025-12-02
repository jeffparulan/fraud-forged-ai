'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { detectFraud, FraudDetectionResponse } from '@/lib/api'
import { AlertCircle } from 'lucide-react'
import { COUNTRIES } from '@/lib/countries'

interface Props {
  onResult: (result: FraudDetectionResponse) => void
  onLoading: (loading: boolean) => void
}

export default function EcommerceForm({ onResult, onLoading }: Props) {
  const [formData, setFormData] = useState({
    order_id: '',
    seller_age_days: '',
    price: '',
    market_price: '',
    amount: '',
    shipping_address: '',
    billing_address: '',
    payment_method: 'credit_card',
    ip_address: '',
    email_verified: false,
    reviews: '',
    shipping_location: '',
    product_details: ''
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    onLoading(true)

    try {
      const reviewList = formData.reviews.split(',').map(r => r.trim()).filter(r => r)
      const result = await detectFraud({
        sector: 'ecommerce',
        data: {
          order_id: formData.order_id || `ORD-${Date.now()}`,
          seller_age_days: parseInt(formData.seller_age_days),
          price: parseFloat(formData.price),
          market_price: parseFloat(formData.market_price),
          amount: parseFloat(formData.amount || formData.price), // Use amount if provided, else price
          shipping_address: formData.shipping_address,
          billing_address: formData.billing_address,
          payment_method: formData.payment_method,
          ip_address: formData.ip_address,
          email_verified: formData.email_verified,
          reviews: reviewList,
          shipping_location: formData.shipping_location,
          product_details: formData.product_details
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

  const SAMPLE_SCENARIOS = [
    {
      name: 'Suspicious Listing (High Risk)',
      data: {
        order_id: 'ORD-2024-12345',
        seller_age_days: '3',
        price: '299',
        market_price: '999',
        amount: '299',
        shipping_address: '123 Unknown St, Unknown City, Unknown Country',
        billing_address: '456 Different Ave, Different City, Different Country',
        payment_method: 'crypto',
        ip_address: 'VPN Detected',
        email_verified: false,
        reviews: 'Excellent product, Excellent seller, Excellent shipping, Excellent quality, Excellent price',
        shipping_location: 'Unknown',
        product_details: 'Luxury watch listed far below market price with stock photos'
      }
    },
    {
      name: 'Legitimate Listing (Low Risk)',
      data: {
        order_id: 'ORD-2024-67890',
        seller_age_days: '730',
        price: '899',
        market_price: '950',
        amount: '899',
        shipping_address: '123 Main St, New York, NY, United States',
        billing_address: '123 Main St, New York, NY, United States',
        payment_method: 'credit_card',
        ip_address: '192.168.1.100',
        email_verified: true,
        reviews: 'Great product, Fast shipping, Good quality, As described, Would buy again',
        shipping_location: 'United States',
        product_details: 'Authentic product from verified seller with detailed photos and description'
      }
    },
    {
      name: 'Moderate Risk Listing (Medium Risk)',
      data: {
        order_id: 'ORD-2024-55555',
        seller_age_days: '45',
        price: '650',
        market_price: '800',
        amount: '650',
        shipping_address: '789 Elm Street, Chicago, IL, United States',
        billing_address: '789 Elm Street, Chicago, IL, United States',
        payment_method: 'credit_card',
        ip_address: '203.0.113.25',
        email_verified: true,
        reviews: 'Good product, Some delays, Mixed reviews, Decent quality, Average service',
        shipping_location: 'United States',
        product_details: 'Product from relatively new seller (45 days) with moderate discount and mixed reviews. Some concerns about shipping delays reported.'
      }
    },
    {
      name: 'Unverified Seller (Medium Risk)',
      data: {
        order_id: 'ORD-2024-33344',
        seller_age_days: '60',
        price: '450',
        market_price: '550',
        amount: '450',
        shipping_address: '555 Market Street, San Francisco, CA, United States',
        billing_address: '555 Market Street, San Francisco, CA, United States',
        payment_method: 'debit_card',
        ip_address: '198.51.100.50',
        email_verified: false,
        reviews: 'Okay product, Slow response, Arrived late, Decent quality, Fair price',
        shipping_location: 'United States',
        product_details: 'Product from 2-month-old seller. Email not verified. Moderate discount. Shipping delays reported.'
      }
    },
    {
      name: 'Potential Return Fraud (High Risk)',
      data: {
        order_id: 'ORD-2024-99999',
        seller_age_days: '15',
        price: '1200',
        market_price: '1800',
        amount: '1200',
        shipping_address: '321 Unknown Road, Unknown City, Unknown State',
        billing_address: '654 Different Street, Another City, Another State',
        payment_method: 'prepaid_card',
        ip_address: 'VPN Detected',
        email_verified: false,
        reviews: 'Perfect, Amazing, Best ever, Incredible, Outstanding',
        shipping_location: 'Unknown',
        product_details: 'High-value electronics from very new seller with suspicious reviews and address mismatch. Significant discount.'
      }
    },
    {
      name: 'Established Seller (Low Risk)',
      data: {
        order_id: 'ORD-2024-11111',
        seller_age_days: '1095',
        price: '1250',
        market_price: '1300',
        amount: '1250',
        shipping_address: '456 Oak Avenue, Los Angeles, CA, United States',
        billing_address: '456 Oak Avenue, Los Angeles, CA, United States',
        payment_method: 'credit_card',
        ip_address: '203.0.113.45',
        email_verified: true,
        reviews: 'Reliable seller, Quality item, Fast delivery, Good packaging, Professional service',
        shipping_location: 'United States',
        product_details: 'Brand new electronics from established seller with 3+ years history and 500+ positive reviews'
      }
    }
  ]

  const loadSample = (index: number = 0) => {
    const sample = SAMPLE_SCENARIOS[index] || SAMPLE_SCENARIOS[0]
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

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Order ID
        </label>
        <input
          type="text"
          value={formData.order_id}
          onChange={(e) => setFormData({ ...formData, order_id: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="ORD-2024-12345"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Seller Account Age (days)
        </label>
        <input
          type="number"
          required
          value={formData.seller_age_days}
          onChange={(e) => setFormData({ ...formData, seller_age_days: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="90"
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Listed Price ($)
          </label>
          <input
            type="number"
            step="0.01"
            required
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="299.99"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Market Price ($)
          </label>
          <input
            type="number"
            step="0.01"
            required
            value={formData.market_price}
            onChange={(e) => setFormData({ ...formData, market_price: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="999.99"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Order Amount ($)
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.amount}
            onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="299.99"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Shipping Address
          </label>
          <input
            type="text"
            value={formData.shipping_address}
            onChange={(e) => setFormData({ ...formData, shipping_address: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="123 Main St, City, Country"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Billing Address
          </label>
          <input
            type="text"
            value={formData.billing_address}
            onChange={(e) => setFormData({ ...formData, billing_address: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="456 Oak Ave, City, Country"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Payment Method
          </label>
          <select
            value={formData.payment_method}
            onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          >
            <option value="credit_card">Credit Card</option>
            <option value="debit_card">Debit Card</option>
            <option value="paypal">PayPal</option>
            <option value="bank_transfer">Bank Transfer</option>
            <option value="crypto">Cryptocurrency</option>
            <option value="gift_card">Gift Card</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            IP Address
          </label>
          <input
            type="text"
            value={formData.ip_address}
            onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="192.168.1.100 or VPN Detected"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Shipping Location (Country)
        </label>
        <select
          required
          value={formData.shipping_location}
          onChange={(e) => setFormData({ ...formData, shipping_location: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
        >
          <option value="">Select a country...</option>
          {COUNTRIES.map((country) => (
            <option key={country} value={country}>
              {country}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Product Details
        </label>
        <textarea
          value={formData.product_details}
          onChange={(e) => setFormData({ ...formData, product_details: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., Luxury watch listed far below market price with stock photos"
          rows={2}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Customer Reviews (comma-separated)
        </label>
        <textarea
          value={formData.reviews}
          onChange={(e) => setFormData({ ...formData, reviews: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., Great product, Fast shipping, Good quality"
          rows={3}
        />
      </div>

      <div className="flex gap-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.email_verified}
            onChange={(e) => setFormData({ ...formData, email_verified: e.target.checked })}
            className="w-5 h-5 rounded border-white/10 bg-nightfall-900 text-sapphire-500 focus:ring-sapphire-500"
          />
          <span className="text-gray-300">Email Verified</span>
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
        className={`w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-semibold transition-opacity ${
          isLoading ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {isLoading ? 'Analyzing...' : 'Analyze Listing'}
      </motion.button>
    </form>
  )
}

