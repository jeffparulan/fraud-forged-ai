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
    name: 'Routine Office Visit (Low Risk)',
    data: {
      claim_id: 'CLM-2024-12345',
      patient_age: '45',
      gender: 'male',
      provider_id: 'PRV-98765',
      specialty: 'Family Medicine',
      diagnosis_codes: 'Z00.00',
      procedure_codes: '99213',
      claim_amount: '150',
      claim_details: 'Annual checkup with basic examination',
      provider_history: 'clean'
    }
  },
  {
    name: 'Upcoding Scheme (High Risk)',
    data: {
      claim_id: 'CLM-2024-78901',
      patient_age: '67',
      gender: 'female',
      provider_id: 'PRV-45821',
      specialty: 'Cardiology',
      diagnosis_codes: 'I25.10, E11.9, I10',
      procedure_codes: '93000, 93015, 93306, 93350, 77080, 71020, 80053, 84443',
      claim_amount: '75000',
      claim_details: 'Comprehensive cardiac workup with multiple imaging studies, extensive lab work. Patient received all tests in single visit.',
      provider_history: 'flagged'
    }
  },
  {
    name: 'Phantom Billing (High Risk)',
    data: {
      claim_id: 'CLM-2024-55123',
      patient_age: '28',
      gender: 'male',
      provider_id: 'PRV-11223',
      specialty: 'Pain Management',
      diagnosis_codes: 'M79.3, M54.5',
      procedure_codes: '64483, 64484, 77003, 99213, 99214',
      claim_amount: '12500',
      claim_details: 'Multiple epidural injections and consultations. Patient records show no visits on claimed dates.',
      provider_history: 'flagged'
    }
  },
  {
    name: 'Unbundling Services (Medium Risk)',
    data: {
      claim_id: 'CLM-2024-33890',
      patient_age: '52',
      gender: 'female',
      provider_id: 'PRV-77432',
      specialty: 'Orthopedic Surgery',
      diagnosis_codes: 'M17.11, M25.561',
      procedure_codes: '27447, 27486, 29881, 29882',
      claim_amount: '28000',
      claim_details: 'Knee replacement surgery with separately billed arthroscopy. Procedures typically bundled together.',
      provider_history: 'clean'
    }
  },
  {
    name: 'Questionable Necessity (Medium Risk)',
    data: {
      claim_id: 'CLM-2024-44556',
      patient_age: '38',
      gender: 'male',
      provider_id: 'PRV-55667',
      specialty: 'Physical Therapy',
      diagnosis_codes: 'M54.5, M25.511',
      procedure_codes: '97110, 97112, 97140, 97530',
      claim_amount: '8500',
      claim_details: 'Extended physical therapy sessions (3x per week for 6 months). No significant improvement documented. Minimal supporting documentation.',
      provider_history: 'clean'
    }
  },
  {
    name: 'Complex but Legitimate Surgery (Low Risk)',
    data: {
      claim_id: 'CLM-2024-66754',
      patient_age: '58',
      gender: 'male',
      provider_id: 'PRV-88990',
      specialty: 'Neurosurgery',
      diagnosis_codes: 'M48.06, G95.11, M50.22',
      procedure_codes: '63081, 22614, 20936',
      claim_amount: '45000',
      claim_details: 'Spinal fusion with instrumentation. Complex multi-level procedure with bone grafting. Well documented medical necessity.',
      provider_history: 'clean'
    }
  }
]

export default function MedicalForm({ onResult, onLoading }: Props) {
  const [formData, setFormData] = useState({
    claim_id: '',
    patient_age: '',
    gender: 'male',
    provider_id: '',
    specialty: '',
    diagnosis_codes: '',
    procedure_codes: '',
    claim_amount: '',
    claim_details: '',
    provider_history: 'clean'
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    onLoading(true)

    try {
      const diagnosisList = formData.diagnosis_codes.split(',').map(c => c.trim()).filter(c => c)
      const procedureList = formData.procedure_codes.split(',').map(c => c.trim()).filter(c => c)
      
      const result = await detectFraud({
        sector: 'medical',
        data: {
          claim_id: formData.claim_id,
          patient_age: parseInt(formData.patient_age),
          gender: formData.gender,
          provider_id: formData.provider_id,
          specialty: formData.specialty,
          diagnosis_codes: diagnosisList,
          procedure_codes: procedureList,
          claim_amount: parseFloat(formData.claim_amount),
          claim_details: formData.claim_details,
          provider_history: formData.provider_history,
          procedures: procedureList,
          diagnosis_mismatch: diagnosisList.length > 0 && procedureList.length > 0 && diagnosisList.length !== procedureList.length
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
            Claim ID
          </label>
          <input
            type="text"
            required
            value={formData.claim_id}
            onChange={(e) => setFormData({ ...formData, claim_id: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="CLM-2024-00001"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Provider ID
          </label>
          <input
            type="text"
            required
            value={formData.provider_id}
            onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="PRV-12345"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Patient Age
          </label>
          <input
            type="number"
            required
            value={formData.patient_age}
            onChange={(e) => setFormData({ ...formData, patient_age: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="45"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Gender
          </label>
          <select
            value={formData.gender}
            onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Specialty
          </label>
          <input
            type="text"
            required
            value={formData.specialty}
            onChange={(e) => setFormData({ ...formData, specialty: e.target.value })}
            className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
            placeholder="e.g., Cardiology"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Diagnosis Codes (ICD-10, comma-separated)
        </label>
        <input
          type="text"
          required
          value={formData.diagnosis_codes}
          onChange={(e) => setFormData({ ...formData, diagnosis_codes: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., I25.10, E11.9, I10"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Procedure Codes (CPT, comma-separated)
        </label>
        <input
          type="text"
          required
          value={formData.procedure_codes}
          onChange={(e) => setFormData({ ...formData, procedure_codes: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., 93000, 93015, 93306"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Claim Amount ($)
        </label>
        <input
          type="number"
          step="0.01"
          required
          value={formData.claim_amount}
          onChange={(e) => setFormData({ ...formData, claim_amount: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="50000.00"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Claim/Procedure Details
        </label>
        <textarea
          required
          value={formData.claim_details}
          onChange={(e) => setFormData({ ...formData, claim_details: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
          placeholder="e.g., Comprehensive cardiac workup with imaging studies"
          rows={3}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Provider History
        </label>
        <select
          value={formData.provider_history}
          onChange={(e) => setFormData({ ...formData, provider_history: e.target.value })}
          className="w-full px-4 py-3 bg-nightfall-900 border border-white/10 rounded-lg text-white focus:border-sapphire-500 focus:outline-none"
        >
          <option value="clean">Clean Record</option>
          <option value="flagged">Previously Flagged</option>
          <option value="warning">Under Review</option>
        </select>
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
        className={`w-full px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-lg font-semibold transition-opacity ${
          isLoading ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {isLoading ? 'Analyzing...' : 'Analyze Claim'}
      </motion.button>
    </form>
  )
}
