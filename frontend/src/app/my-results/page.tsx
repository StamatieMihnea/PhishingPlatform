'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { dashboardApi } from '@/lib/api'
import { CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

export default function MyResultsPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'USER') {
      router.push('/dashboard')
      return
    }
    fetchResults()
  }, [isAuthenticated, user, router])

  const fetchResults = async () => {
    try {
      const data = await dashboardApi.myResults()
      setResults(data || [])
    } catch (error) {
      console.error('Error fetching results:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">My Phishing Test Results</h1>
          <p className="text-secondary-500 mt-1">See how you performed in phishing awareness tests</p>
        </div>

        {results.length === 0 ? (
          <div className="card text-center py-12">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-secondary-900">No test results yet</h3>
            <p className="text-secondary-500 mt-1">You haven't been included in any completed phishing tests</p>
          </div>
        ) : (
          <div className="space-y-4">
            {results.map((result, index) => (
              <div key={index} className="card">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <div className={`p-3 rounded-full ${result.was_phished ? 'bg-red-100' : 'bg-green-100'}`}>
                      {result.was_phished ? (
                        <XCircle className="h-6 w-6 text-red-600" />
                      ) : (
                        <CheckCircle className="h-6 w-6 text-green-600" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-semibold text-secondary-900">{result.campaign_name}</h3>
                      <p className="text-sm text-secondary-500 mt-1">
                        Test sent: {result.email_sent_at ? new Date(result.email_sent_at).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                    result.was_phished ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {result.was_phished ? 'Failed' : 'Passed'}
                  </span>
                </div>

                <div className="mt-4 pt-4 border-t border-secondary-200">
                  <h4 className="text-sm font-medium text-secondary-700 mb-3">Your Actions:</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className={`p-3 rounded-lg ${result.email_opened ? 'bg-yellow-50' : 'bg-secondary-50'}`}>
                      <p className="text-xs text-secondary-500">Email Opened</p>
                      <p className={`font-medium ${result.email_opened ? 'text-yellow-700' : 'text-secondary-400'}`}>
                        {result.email_opened ? 'Yes' : 'No'}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${result.link_clicked ? 'bg-orange-50' : 'bg-secondary-50'}`}>
                      <p className="text-xs text-secondary-500">Link Clicked</p>
                      <p className={`font-medium ${result.link_clicked ? 'text-orange-700' : 'text-secondary-400'}`}>
                        {result.link_clicked ? 'Yes' : 'No'}
                      </p>
                    </div>
                    <div className={`p-3 rounded-lg ${result.credentials_submitted ? 'bg-red-50' : 'bg-secondary-50'}`}>
                      <p className="text-xs text-secondary-500">Credentials Entered</p>
                      <p className={`font-medium ${result.credentials_submitted ? 'text-red-700' : 'text-secondary-400'}`}>
                        {result.credentials_submitted ? 'Yes' : 'No'}
                      </p>
                    </div>
                    <div className="p-3 bg-secondary-50 rounded-lg">
                      <p className="text-xs text-secondary-500">Result</p>
                      <p className={`font-medium ${result.was_phished ? 'text-red-600' : 'text-green-600'}`}>
                        {result.was_phished ? 'Needs Improvement' : 'Great Job!'}
                      </p>
                    </div>
                  </div>
                </div>

                {result.was_phished && (
                  <div className="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                    <div className="flex items-start space-x-3">
                      <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-yellow-800">What you could have noticed:</p>
                        <ul className="mt-2 text-sm text-yellow-700 list-disc list-inside space-y-1">
                          <li>Check the sender's email address for inconsistencies</li>
                          <li>Hover over links before clicking to see the actual URL</li>
                          <li>Be wary of urgent requests for personal information</li>
                          <li>When in doubt, verify through official channels</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}
