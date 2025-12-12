'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import Table from '@/components/Table'
import Modal from '@/components/Modal'
import StatsCard from '@/components/StatsCard'
import { useAuthStore } from '@/lib/store'
import { companiesApi } from '@/lib/api'
import { Company, CompanyStats } from '@/types'
import { Plus, Building2, Users, Target, Trash2 } from 'lucide-react'

export default function CompaniesPage() {
  const router = useRouter()
  const { isAuthenticated, user } = useAuthStore()
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showStatsModal, setShowStatsModal] = useState(false)
  const [selectedStats, setSelectedStats] = useState<CompanyStats | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    domain: '',
    logo_url: '',
  })

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'SUPER_ADMIN') {
      router.push('/dashboard')
      return
    }
    fetchCompanies()
  }, [isAuthenticated, user, router])

  const fetchCompanies = async () => {
    try {
      const data = await companiesApi.list()
      setCompanies(data.companies || [])
    } catch (error) {
      console.error('Error fetching companies:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await companiesApi.create(formData)
      setShowCreateModal(false)
      setFormData({ name: '', domain: '', logo_url: '' })
      fetchCompanies()
    } catch (error) {
      console.error('Error creating company:', error)
    }
  }

  const handleViewStats = async (company: Company) => {
    try {
      const stats = await companiesApi.stats(company.id)
      setSelectedStats(stats)
      setShowStatsModal(true)
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to deactivate this company?')) return
    try {
      await companiesApi.delete(id)
      fetchCompanies()
    } catch (error) {
      console.error('Error deleting company:', error)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Company',
      render: (company: Company) => (
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <Building2 className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <p className="font-medium text-secondary-900">{company.name}</p>
            <p className="text-sm text-secondary-500">{company.domain}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (company: Company) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          company.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          {company.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (company: Company) => new Date(company.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (company: Company) => (
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleViewStats(company); }}
            className="px-3 py-1 text-sm text-primary-600 hover:bg-primary-50 rounded-lg"
          >
            View Stats
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(company.id); }}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ]

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-secondary-900">Companies</h1>
            <p className="text-secondary-500 mt-1">Manage platform companies</p>
          </div>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center">
            <Plus className="h-5 w-5 mr-2" />
            Add Company
          </button>
        </div>

        <Table
          columns={columns}
          data={companies}
          keyExtractor={(c) => c.id}
          emptyMessage="No companies yet"
        />

        {/* Create Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Add New Company"
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="label">Company Name</label>
              <input
                type="text"
                className="input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Domain</label>
              <input
                type="text"
                className="input"
                value={formData.domain}
                onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                placeholder="company.com"
                required
              />
            </div>
            <div>
              <label className="label">Logo URL (optional)</label>
              <input
                type="url"
                className="input"
                value={formData.logo_url}
                onChange={(e) => setFormData({ ...formData, logo_url: e.target.value })}
                placeholder="https://..."
              />
            </div>
            <div className="flex justify-end space-x-3 pt-4">
              <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create Company
              </button>
            </div>
          </form>
        </Modal>

        {/* Stats Modal */}
        <Modal
          isOpen={showStatsModal}
          onClose={() => setShowStatsModal(false)}
          title={`Stats: ${selectedStats?.company_name}`}
          size="lg"
        >
          {selectedStats && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <StatsCard
                  title="Total Users"
                  value={selectedStats.total_users}
                  icon={Users}
                />
                <StatsCard
                  title="Total Campaigns"
                  value={selectedStats.total_campaigns}
                  icon={Target}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-secondary-50 rounded-lg">
                  <p className="text-sm text-secondary-500">Emails Sent</p>
                  <p className="text-2xl font-bold text-secondary-900">{selectedStats.total_emails_sent}</p>
                </div>
                <div className="p-4 bg-secondary-50 rounded-lg">
                  <p className="text-sm text-secondary-500">Emails Opened</p>
                  <p className="text-2xl font-bold text-secondary-900">{selectedStats.total_emails_opened}</p>
                </div>
                <div className="p-4 bg-secondary-50 rounded-lg">
                  <p className="text-sm text-secondary-500">Links Clicked</p>
                  <p className="text-2xl font-bold text-secondary-900">{selectedStats.total_links_clicked}</p>
                </div>
                <div className="p-4 bg-secondary-50 rounded-lg">
                  <p className="text-sm text-secondary-500">Credentials Submitted</p>
                  <p className="text-2xl font-bold text-secondary-900">{selectedStats.total_credentials_submitted}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-orange-50 rounded-lg">
                  <p className="text-sm text-orange-600">Click Rate</p>
                  <p className="text-2xl font-bold text-orange-700">{selectedStats.click_rate}%</p>
                </div>
                <div className="p-4 bg-red-50 rounded-lg">
                  <p className="text-sm text-red-600">Submission Rate</p>
                  <p className="text-2xl font-bold text-red-700">{selectedStats.submission_rate}%</p>
                </div>
              </div>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  )
}
