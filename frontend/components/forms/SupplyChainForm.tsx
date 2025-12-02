'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { detectFraud, FraudDetectionResponse } from '@/lib/api'
import { AlertCircle } from 'lucide-react'

interface Props {
  onResult: (result: FraudDetectionResponse) => void
  onLoading: (loading: boolean) => void
}

const SAMPLE_SCENARIOS = [
  {
    name: 'Legitimate Supplier (Low Risk)',
    data: {
      supplier_id: 'SUP-2024-12345',
      supplier_name: 'Acme Manufacturing Co',
      order_amount: '25000',
      order_frequency: '12',
      payment_terms: 'NET30',
      supplier_age_days: '1825',
      delivery_variance: '2',
      quality_issues: '0',
      price_variance: '5',
      documentation_complete: true,
      regulatory_compliance: true,
      order_details: 'Regular component order, established supplier with 5-year history'
    }
  },
  {
    name: 'Trusted Partner (Low Risk)',
    data: {
      supplier_id: 'SUP-2024-55432',
      supplier_name: 'TechComponents Direct',
      order_amount: '180000',
      order_frequency: '8',
      payment_terms: 'NET45',
      supplier_age_days: '1095',
      delivery_variance: '3',
      quality_issues: '0',
      price_variance: '7',
      documentation_complete: true,
      regulatory_compliance: true,
      order_details: 'Large seasonal order for Q4. Established supplier, competitive pricing, full documentation'
    }
  },
  {
    name: 'Invoice Padding (Medium Risk)',
    data: {
      supplier_id: 'SUP-2024-77654',
      supplier_name: 'Global Logistics Partners',
      order_amount: '45000',
      order_frequency: '18',
      payment_terms: 'NET30',
      supplier_age_days: '365',
      delivery_variance: '8',
      quality_issues: '1',
      price_variance: '18',
      documentation_complete: true,
      regulatory_compliance: true,
      order_details: 'Invoices include ambiguous line items, duplicate charges, inflated shipping costs'
    }
  },
  {
    name: 'Quality Concerns (Medium Risk)',
    data: {
      supplier_id: 'SUP-2024-66778',
      supplier_name: 'Budget Parts Supply',
      order_amount: '32000',
      order_frequency: '15',
      payment_terms: 'NET30',
      supplier_age_days: '180',
      delivery_variance: '12',
      quality_issues: '4',
      price_variance: '22',
      documentation_complete: true,
      regulatory_compliance: true,
      order_details: 'Lower-priced supplier with some quality issues and delivery delays. Documentation appears complete but products below specification'
    }
  },
  {
    name: 'Ghost Supplier Scheme (High Risk)',
    data: {
      supplier_id: 'SUP-2024-99887',
      supplier_name: 'QuickParts Ltd',
      order_amount: '150000',
      order_frequency: '1',
      payment_terms: 'ADVANCE',
      supplier_age_days: '5',
      delivery_variance: '100',
      quality_issues: '0',
      price_variance: '45',
      documentation_complete: false,
      regulatory_compliance: false,
      order_details: 'Large advance payment requested. Supplier has no online presence, unverified address, no references'
    }
  },
  {
    name: 'Kickback Scheme (High Risk)',
    data: {
      supplier_id: 'SUP-2024-44231',
      supplier_name: 'Premium Supplies Inc',
      order_amount: '85000',
      order_frequency: '24',
      payment_terms: 'NET15',
      supplier_age_days: '90',
      delivery_variance: '5',
      quality_issues: '3',
      price_variance: '35',
      documentation_complete: true,
      regulatory_compliance: true,
      order_details: 'Prices 35% above market rate. Purchasing manager has personal relationship with supplier. Inferior quality products.'
    }
  }
]

export default function SupplyChainForm({ onResult, onLoading }: Props) {
  const [formData, setFormData] = useState({
    supplier_id: '',
    supplier_name: '',
    order_amount: '',
    order_frequency: '',
    payment_terms: 'NET30',
    supplier_age_days: '',
    delivery_variance: '',
    quality_issues: '',
    price_variance: '',
    documentation_complete: true,
    regulatory_compliance: true,
    order_details: ''
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    onLoading(true)

    try {
      const result = await detectFraud({
        sector: 'supply_chain',
        data: {
          supplier_id: formData.supplier_id,
          supplier_name: formData.supplier_name,
          order_amount: parseFloat(formData.order_amount),
          order_frequency: parseInt(formData.order_frequency),
          payment_terms: formData.payment_terms,
          supplier_age_days: parseInt(formData.supplier_age_days),
          delivery_variance: parseFloat(formData.delivery_variance),
          quality_issues: parseInt(formData.quality_issues),
          price_variance: parseFloat(formData.price_variance),
          documentation_complete: formData.documentation_complete,
          regulatory_compliance: formData.regulatory_compliance,
          order_details: formData.order_details
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

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Supplier ID
        </label>
        <input
          type="text"
          value={formData.supplier_id}
          onChange={(e) => setFormData({ ...formData, supplier_id: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="SUP-2024-00001"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Supplier Name
        </label>
        <input
          type="text"
          required
          value={formData.supplier_name}
          onChange={(e) => setFormData({ ...formData, supplier_name: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="Acme Manufacturing Co"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Order Amount ($)
          </label>
          <input
            type="number"
            step="0.01"
            required
            value={formData.order_amount}
            onChange={(e) => setFormData({ ...formData, order_amount: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="25000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Order Frequency (per year)
          </label>
          <input
            type="number"
            required
            value={formData.order_frequency}
            onChange={(e) => setFormData({ ...formData, order_frequency: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="12"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Payment Terms
          </label>
          <select
            value={formData.payment_terms}
            onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          >
            <option value="NET30">NET30</option>
            <option value="NET45">NET45</option>
            <option value="NET60">NET60</option>
            <option value="NET15">NET15</option>
            <option value="ADVANCE">Advance Payment</option>
            <option value="COD">Cash on Delivery</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Supplier Age (days)
          </label>
          <input
            type="number"
            required
            value={formData.supplier_age_days}
            onChange={(e) => setFormData({ ...formData, supplier_age_days: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="365"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Delivery Variance (%)
          </label>
          <input
            type="number"
            step="0.1"
            required
            value={formData.delivery_variance}
            onChange={(e) => setFormData({ ...formData, delivery_variance: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="5"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Quality Issues (count)
          </label>
          <input
            type="number"
            required
            value={formData.quality_issues}
            onChange={(e) => setFormData({ ...formData, quality_issues: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="0"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Price Variance (%)
          </label>
          <input
            type="number"
            step="0.1"
            required
            value={formData.price_variance}
            onChange={(e) => setFormData({ ...formData, price_variance: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="5"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Order Details
        </label>
        <textarea
          value={formData.order_details}
          onChange={(e) => setFormData({ ...formData, order_details: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., Regular component order, established supplier with 5-year history"
          rows={3}
        />
      </div>

      <div className="flex gap-6">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.documentation_complete}
            onChange={(e) => setFormData({ ...formData, documentation_complete: e.target.checked })}
            className="w-5 h-5 rounded border-white/10 bg-nightfall-900 text-sapphire-500 focus:ring-sapphire-500"
          />
          <span className="text-gray-300">Documentation Complete</span>
        </label>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.regulatory_compliance}
            onChange={(e) => setFormData({ ...formData, regulatory_compliance: e.target.checked })}
            className="w-5 h-5 rounded border-white/10 bg-nightfall-900 text-sapphire-500 focus:ring-sapphire-500"
          />
          <span className="text-gray-300">Regulatory Compliance</span>
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
        className={`w-full px-6 py-3 bg-gradient-to-r from-orange-600 to-amber-600 text-white rounded-lg font-semibold transition-opacity ${
          isLoading ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {isLoading ? 'Analyzing...' : 'Analyze Supply Chain Order'}
      </motion.button>
    </form>
  )
}


