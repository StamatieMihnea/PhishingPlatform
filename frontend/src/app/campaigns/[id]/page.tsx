'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Layout from '@/components/Layout'
import StatsCard from '@/components/StatsCard'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { campaignsApi } from '@/lib/api'
import { Campaign, CampaignStats, CampaignTarget } from '@/types'
import {
  ArrowLeft,
  Play,
  Square,
  Calendar,
  Users,
  Mail,
  MousePointerClick,
  Key,
  Eye,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

export default function CampaignDetailPage() {
  const router = useRouter()
  const params = useParams()
  const { isAuthenticated } = useAuthStore()
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [stats, setStats] = useState<CampaignStats | null>(null)
  const [targets, setTargets] = useState<CampaignTarget[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    fetchData()
  }, [isAuthenticated, router, params.id])

  const fetchData = async () => {
    try {
      const [campaignData, statsData, targetsData] = await Promise.all([
        campaignsApi.get(params.id as string),
        campaignsApi.stats(params.id as string),
        campaignsApi.targets(params.id as string),
      ])
      setCampaign(campaignData)
      setStats(statsData)
      setTargets(targetsData.targets || [])
    } catch (error) {
      console.error('Error fetching campaign:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleStart = async () => {
    try {
      await campaignsApi.start(params.id as string)
      fetchData()
    } catch (error) {
      console.error('Error starting campaign:', error)
    }
  }

  const handleStop = async () => {
    try {
      await campaignsApi.stop(params.id as string)
      fetchData()
    } catch (error) {
      console.error('Error stopping campaign:', error)
    }
  }

  if (loading || !campaign) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </Layout>
    )
  }

  const chartData = [
    { name: 'Sent', value: stats?.emails_sent || 0 },
    { name: 'Opened', value: stats?.emails_opened || 0 },
    { name: 'Clicked', value: stats?.links_clicked || 0 },
    { name: 'Submitted', value: stats?.credentials_submitted || 0 },
  ]

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push('/campaigns')}
              className="p-2 hover:bg-secondary-100 rounded-lg"
            >
              <ArrowLeft className="h-5 w-5 text-secondary-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-secondary-900">{campaign.name}</h1>
              <p className="text-secondary-500 mt-1">{campaign.description}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <StatusBadge status={campaign.status} />
            {campaign.status === 'DRAFT' && (
              <button onClick={handleStart} className="btn-primary flex items-center">
                <Play className="h-4 w-4 mr-2" />
                Start Campaign
              </button>
            )}
            {campaign.status === 'RUNNING' && (
              <button onClick={handleStop} className="btn-danger flex items-center">
                <Square className="h-4 w-4 mr-2" />
                Stop Campaign
              </button>
            )}
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatsCard
            title="Total Targets"
            value={stats?.total_targets || 0}
            icon={Users}
          />
          <StatsCard
            title="Emails Sent"
            value={stats?.emails_sent || 0}
            icon={Mail}
          />
          <StatsCard
            title="Click Rate"
            value={`${stats?.click_rate || 0}%`}
            icon={MousePointerClick}
            changeType={stats?.click_rate && stats.click_rate > 50 ? 'negative' : 'positive'}
          />
          <StatsCard
            title="Submission Rate"
            value={`${stats?.submission_rate || 0}%`}
            icon={Key}
            changeType={stats?.submission_rate && stats.submission_rate > 20 ? 'negative' : 'positive'}
          />
        </div>

        {/* Chart */}
        <div className="card">
          <h3 className="text-lg font-semibold text-secondary-900 mb-4">Campaign Funnel</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Targets List */}
        <div className="card">
          <h3 className="text-lg font-semibold text-secondary-900 mb-4">Target Users</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-secondary-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">User</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Email Sent</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Opened</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Clicked</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Submitted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-secondary-200">
                {targets.map((target) => (
                  <tr key={target.id}>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-secondary-900">{target.user_name}</p>
                        <p className="text-sm text-secondary-500">{target.user_email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {target.email_sent ? (
                        <span className="text-green-600">✓ {target.email_sent_at && new Date(target.email_sent_at).toLocaleString()}</span>
                      ) : (
                        <span className="text-secondary-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {target.email_opened ? (
                        <span className="text-yellow-600">✓</span>
                      ) : (
                        <span className="text-secondary-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {target.link_clicked ? (
                        <span className="text-orange-600">✓</span>
                      ) : (
                        <span className="text-secondary-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {target.credentials_submitted ? (
                        <span className="text-red-600">✓</span>
                      ) : (
                        <span className="text-secondary-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  )
}
