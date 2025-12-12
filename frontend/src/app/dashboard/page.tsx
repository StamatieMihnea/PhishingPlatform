'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import StatsCard from '@/components/StatsCard'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { dashboardApi, campaignsApi, companiesApi } from '@/lib/api'
import {
  Target,
  Users,
  Mail,
  MousePointerClick,
  Shield,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

export default function DashboardPage() {
  const router = useRouter()
  const { user, isAuthenticated } = useAuthStore()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<any>(null)
  const [campaigns, setCampaigns] = useState<any[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    fetchDashboardData()
  }, [isAuthenticated, router])

  const fetchDashboardData = async () => {
    try {
      if (user?.role === 'USER') {
        // User dashboard
        const [statsData, campaignsData, recsData] = await Promise.all([
          dashboardApi.myStats(),
          dashboardApi.myCampaigns(),
          dashboardApi.recommendations(),
        ])
        setStats(statsData)
        setCampaigns(campaignsData)
        setRecommendations(recsData)
      } else {
        // Admin dashboard
        const campaignsData = await campaignsApi.list()
        setCampaigns(campaignsData.campaigns || [])
        
        // Calculate stats from campaigns
        const totalCampaigns = campaignsData.campaigns?.length || 0
        const runningCampaigns = campaignsData.campaigns?.filter((c: any) => c.status === 'RUNNING').length || 0
        const completedCampaigns = campaignsData.campaigns?.filter((c: any) => c.status === 'COMPLETED').length || 0
        
        setStats({
          total_campaigns: totalCampaigns,
          running_campaigns: runningCampaigns,
          completed_campaigns: completedCampaigns,
        })
      }
    } catch (error) {
      console.error('Error fetching dashboard data:', error)
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

  // User Dashboard
  if (user?.role === 'USER') {
    const pieData = [
      { name: 'Passed', value: stats?.campaigns_passed || 0, color: '#22c55e' },
      { name: 'Failed', value: stats?.campaigns_failed || 0, color: '#ef4444' },
    ]

    return (
      <Layout>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-secondary-900">My Security Dashboard</h1>
            <p className="text-secondary-500 mt-1">Track your phishing awareness progress</p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatsCard
              title="Total Tests"
              value={stats?.total_campaigns || 0}
              icon={Target}
            />
            <StatsCard
              title="Tests Passed"
              value={stats?.campaigns_passed || 0}
              icon={CheckCircle}
              changeType="positive"
            />
            <StatsCard
              title="Tests Failed"
              value={stats?.campaigns_failed || 0}
              icon={AlertTriangle}
              changeType="negative"
            />
            <StatsCard
              title="Success Rate"
              value={`${stats?.success_rate || 100}%`}
              icon={TrendingUp}
              changeType={stats?.success_rate >= 80 ? 'positive' : 'negative'}
            />
          </div>

          {/* Charts and Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Chart */}
            <div className="card">
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Your Performance</h3>
              {stats?.total_campaigns > 0 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-secondary-500">
                  No test results yet
                </div>
              )}
            </div>

            {/* Recommendations */}
            <div className="card">
              <h3 className="text-lg font-semibold text-secondary-900 mb-4">Security Recommendations</h3>
              {recommendations.length > 0 ? (
                <div className="space-y-3">
                  {recommendations.slice(0, 4).map((rec: any) => (
                    <div key={rec.id} className="p-3 bg-secondary-50 rounded-lg">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="font-medium text-secondary-900">{rec.title}</p>
                          <p className="text-sm text-secondary-500 mt-1">{rec.description}</p>
                        </div>
                        <StatusBadge status={rec.priority} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-secondary-500">No recommendations at this time. Great job!</p>
              )}
            </div>
          </div>

          {/* Recent Campaigns */}
          <div className="card">
            <h3 className="text-lg font-semibold text-secondary-900 mb-4">Recent Phishing Tests</h3>
            {campaigns.length > 0 ? (
              <div className="space-y-3">
                {campaigns.slice(0, 5).map((campaign: any) => (
                  <div key={campaign.id} className="flex items-center justify-between p-3 bg-secondary-50 rounded-lg">
                    <div>
                      <p className="font-medium text-secondary-900">{campaign.name}</p>
                      <p className="text-sm text-secondary-500">{campaign.description}</p>
                    </div>
                    <StatusBadge status={campaign.status} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-secondary-500">No tests assigned yet</p>
            )}
          </div>
        </div>
      </Layout>
    )
  }

  // Admin Dashboard
  const chartData = campaigns.slice(0, 6).map((c: any) => ({
    name: c.name.substring(0, 15),
    status: c.status,
  }))

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Dashboard</h1>
          <p className="text-secondary-500 mt-1">
            {user?.role === 'SUPER_ADMIN' ? 'Platform overview' : 'Company overview'}
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatsCard
            title="Total Campaigns"
            value={stats?.total_campaigns || 0}
            icon={Target}
          />
          <StatsCard
            title="Running Campaigns"
            value={stats?.running_campaigns || 0}
            icon={Mail}
            changeType="info"
          />
          <StatsCard
            title="Completed"
            value={stats?.completed_campaigns || 0}
            icon={CheckCircle}
            changeType="positive"
          />
          <StatsCard
            title="Total Users"
            value={stats?.total_users || '-'}
            icon={Users}
          />
        </div>

        {/* Recent Campaigns */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-secondary-900">Recent Campaigns</h3>
            <button
              onClick={() => router.push('/campaigns')}
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              View all →
            </button>
          </div>
          {campaigns.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-secondary-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-secondary-500 uppercase">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-secondary-200">
                  {campaigns.slice(0, 5).map((campaign: any) => (
                    <tr key={campaign.id} className="hover:bg-secondary-50 cursor-pointer" onClick={() => router.push(`/campaigns/${campaign.id}`)}>
                      <td className="px-4 py-3 text-sm font-medium text-secondary-900">{campaign.name}</td>
                      <td className="px-4 py-3"><StatusBadge status={campaign.status} /></td>
                      <td className="px-4 py-3 text-sm text-secondary-500">
                        {new Date(campaign.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-secondary-500 text-center py-8">No campaigns yet</p>
          )}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <button
            onClick={() => router.push('/campaigns/new')}
            className="card hover:border-primary-300 hover:shadow-md transition-all text-left"
          >
            <Target className="h-8 w-8 text-primary-600 mb-3" />
            <h4 className="font-semibold text-secondary-900">Create Campaign</h4>
            <p className="text-sm text-secondary-500 mt-1">Start a new phishing simulation</p>
          </button>
          <button
            onClick={() => router.push('/users')}
            className="card hover:border-primary-300 hover:shadow-md transition-all text-left"
          >
            <Users className="h-8 w-8 text-primary-600 mb-3" />
            <h4 className="font-semibold text-secondary-900">Manage Users</h4>
            <p className="text-sm text-secondary-500 mt-1">Add or manage employee accounts</p>
          </button>
          <button
            onClick={() => router.push('/templates')}
            className="card hover:border-primary-300 hover:shadow-md transition-all text-left"
          >
            <Mail className="h-8 w-8 text-primary-600 mb-3" />
            <h4 className="font-semibold text-secondary-900">Email Templates</h4>
            <p className="text-sm text-secondary-500 mt-1">Create phishing email templates</p>
          </button>
        </div>
      </div>
    </Layout>
  )
}
