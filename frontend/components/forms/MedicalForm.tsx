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
      claim_details:
        'Established patient annual wellness visit. Review of systems negative. Vitals stable. ' +
        'Physical exam age-appropriate. Counseling on diet and exercise. No acute complaints. ' +
        'Assessment: general adult medical examination (Z00.00). Plan: routine labs next year.',
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
      procedure_codes: '93000, 93015, 93306, 93350, 71020, 80053',
      claim_amount: '45000',
      claim_details:
        'Cardiology note: CAD (I25.10), T2DM (E11.9), HTN (I10). Same-day billed ECG (93000), stress test (93015), ' +
        'echo (93306), stress echo (93350), chest x-ray (71020), CMP (80053). ' +
        'Patient received all tests in a single visit. Intensity of testing exceeds documented clinical indication.',
      provider_history: 'flagged'
    }
  },
  {
    name: 'Phantom Billing (Critical Risk)',
    data: {
      claim_id: 'CLM-2024-55123',
      patient_age: '28',
      gender: 'male',
      provider_id: 'PRV-11223',
      specialty: 'Pain Management',
      diagnosis_codes: 'M79.3, M54.5',
      procedure_codes: '64483, 64484, 77003, 99213',
      claim_amount: '22000',
      claim_details:
        'Claim lists lumbar epidural injections (64483/64484), fluoro guidance (77003), and E/M visit (99213) ' +
        'for myalgia (M79.3) and low back pain (M54.5). Clinic schedule and EHR show no visits on the claimed dates. ' +
        'No consent or vitals recorded for the billed injection dates.',
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
      claim_details:
        'Operative note: Right total knee arthroplasty (CPT 27447) for primary OA (M17.11) with knee pain (M25.561). ' +
        'Same encounter also billed revision component (27486) plus arthroscopic meniscectomy/repair (29881, 29882). ' +
        'Arthroscopy was performed in the same operative session as the arthroplasty. ' +
        'Billing concern: arthroscopy and arthroplasty components are typically bundled rather than billed separately.',
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
      claim_details:
        'PT progress note: low back pain (M54.5) and shoulder pain (M25.511). Treatment includes therapeutic exercise (97110), ' +
        'neuromuscular re-ed (97112), manual therapy (97140), and therapeutic activities (97530), 3x/week for 6 months. ' +
        'Functional scores unchanged across reassessments. No significant improvement documented. Minimal supporting documentation.',
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
      claim_details:
        'Operative note: Cervical corpectomy (63081) with arthrodesis (22614) and autograft (20936) for spinal stenosis (M48.06), ' +
        'myelopathy (G95.11), and cervical disc disorder (M50.22). Progressive neurologic deficits documented. MRI correlation present. ' +
        'Operative findings and decompression results documented. Complex multi-level procedure with bone grafting. ' +
        'Well documented medical necessity and consent.',
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
  const [selectedSampleIndex, setSelectedSampleIndex] = useState<number | null>(null)

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
          // Do NOT flag diagnosis_mismatch from ICD vs CPT count inequality —
          // unequal counts are normal in claims and were falsely pushing Medium
          // samples (e.g. Unbundling) to CRITICAL (+40).
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
    setSelectedSampleIndex(index)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Sample Scenario Buttons */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-300 mb-3">
          Load Sample Scenario:
        </label>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-2">
          {SAMPLE_SCENARIOS.map((scenario, index) => {
            const selected = selectedSampleIndex === index
            return (
              <button
                key={index}
                type="button"
                onClick={() => loadSample(index)}
                aria-pressed={selected}
                className={`px-3 py-2 text-xs rounded transition-colors text-left border ${
                  selected
                    ? 'bg-sapphire-500/25 border-sapphire-400 text-white ring-1 ring-sapphire-400/60'
                    : 'glass-effect border-transparent text-white hover:bg-white/10'
                }`}
              >
                {scenario.name}
              </button>
            )
          })}
        </div>
        {selectedSampleIndex !== null && (
          <p className="mt-3 text-sm text-sapphire-300">
            Selected scenario:{' '}
            <span className="font-semibold text-white">
              {SAMPLE_SCENARIOS[selectedSampleIndex].name}
            </span>
          </p>
        )}
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
