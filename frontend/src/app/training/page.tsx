'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import { useAuthStore } from '@/lib/store'
import { dashboardApi } from '@/lib/api'
import { GraduationCap, CheckCircle, PlayCircle, BookOpen, Shield, Link2, AlertTriangle } from 'lucide-react'

export default function TrainingPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const [materials, setMaterials] = useState<any[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'USER') {
      router.push('/dashboard')
      return
    }
    fetchData()
  }, [isAuthenticated, user, router])

  const fetchData = async () => {
    try {
      const [materialsData, recsData] = await Promise.all([
        dashboardApi.training(),
        dashboardApi.recommendations(),
      ])
      setMaterials(materialsData || [])
      setRecommendations(recsData || [])
    } catch (error) {
      console.error('Error fetching training data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async (id: string) => {
    try {
      await dashboardApi.completeTraining(id)
      fetchData()
    } catch (error) {
      console.error('Error completing training:', error)
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'email_security': return <Shield className="h-6 w-6" />
      case 'passwords': return <BookOpen className="h-6 w-6" />
      case 'links': return <Link2 className="h-6 w-6" />
      default: return <GraduationCap className="h-6 w-6" />
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
          <h1 className="text-2xl font-bold text-secondary-900">Security Training</h1>
          <p className="text-secondary-500 mt-1">Improve your security awareness with these resources</p>
        </div>

        {/* Personalized Recommendations */}
        {recommendations.length > 0 && (
          <div className="card border-l-4 border-l-yellow-500">
            <div className="flex items-start space-x-3">
              <AlertTriangle className="h-6 w-6 text-yellow-500 flex-shrink-0" />
              <div>
                <h3 className="font-semibold text-secondary-900">Personalized Recommendations</h3>
                <p className="text-sm text-secondary-500 mt-1">Based on your phishing test results</p>
                <div className="mt-4 space-y-3">
                  {recommendations.map((rec) => (
                    <div key={rec.id} className="p-3 bg-yellow-50 rounded-lg">
                      <p className="font-medium text-secondary-900">{rec.title}</p>
                      <p className="text-sm text-secondary-600 mt-1">{rec.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Training Materials */}
        <div>
          <h2 className="text-lg font-semibold text-secondary-900 mb-4">Training Modules</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {materials.map((material) => (
              <div key={material.id} className="card hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-4">
                    <div className="p-3 bg-primary-100 rounded-xl text-primary-600">
                      {getCategoryIcon(material.category)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-secondary-900">{material.title}</h3>
                      <p className="text-sm text-secondary-500 mt-1">{material.description}</p>
                    </div>
                  </div>
                  {material.completed && (
                    <CheckCircle className="h-6 w-6 text-green-500 flex-shrink-0" />
                  )}
                </div>
                <div className="mt-4 flex justify-end">
                  {material.completed ? (
                    <span className="text-sm text-green-600 font-medium">Completed</span>
                  ) : (
                    <button
                      onClick={() => handleComplete(material.id)}
                      className="btn-primary flex items-center text-sm"
                    >
                      <PlayCircle className="h-4 w-4 mr-2" />
                      Start Training
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Tips */}
        <div className="card bg-gradient-to-r from-primary-50 to-primary-100">
          <h3 className="font-semibold text-secondary-900 mb-4">Quick Security Tips</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">🔍 Verify Senders</p>
              <p className="text-sm text-secondary-500 mt-1">Always check the sender's email address carefully</p>
            </div>
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">🖱️ Hover Before Clicking</p>
              <p className="text-sm text-secondary-500 mt-1">Preview URLs before clicking any links</p>
            </div>
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">⏰ Watch for Urgency</p>
              <p className="text-sm text-secondary-500 mt-1">Be skeptical of urgent requests</p>
            </div>
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">🔐 Use Strong Passwords</p>
              <p className="text-sm text-secondary-500 mt-1">Create unique passwords for each account</p>
            </div>
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">📱 Enable 2FA</p>
              <p className="text-sm text-secondary-500 mt-1">Add an extra layer of security</p>
            </div>
            <div className="p-4 bg-white rounded-lg">
              <p className="font-medium text-secondary-900">📢 Report Suspicious Emails</p>
              <p className="text-sm text-secondary-500 mt-1">Alert IT when something seems off</p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
