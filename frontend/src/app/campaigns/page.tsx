'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import Table from '@/components/Table'
import Modal from '@/components/Modal'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { campaignsApi, templatesApi, usersApi } from '@/lib/api'
import { Campaign, EmailTemplate, User } from '@/types'
import { Plus, Target, Play, Square, Calendar, Trash2 } from 'lucide-react'

export default function CampaignsPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    template_id: '',
    target_user_ids: [] as string[],
  })

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    fetchData()
  }, [isAuthenticated, router])

  const fetchData = async () => {
    try {
      const [campaignsData, templatesData, usersData] = await Promise.all([
        campaignsApi.list(),
        templatesApi.list(),
        usersApi.list(),
      ])
      setCampaigns(campaignsData.campaigns || [])
      setTemplates(templatesData.templates || [])
      setUsers(usersData.users || [])
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await campaignsApi.create(formData)
      setShowCreateModal(false)
      setFormData({ name: '', description: '', template_id: '', target_user_ids: [] })
      fetchData()
    } catch (error) {
      console.error('Error creating campaign:', error)
    }
  }

  const handleStart = async (id: string) => {
    try {
      await campaignsApi.start(id)
      fetchData()
    } catch (error) {
      console.error('Error starting campaign:', error)
    }
  }

  const handleStop = async (id: string) => {
    try {
      await campaignsApi.stop(id)
      fetchData()
    } catch (error) {
      console.error('Error stopping campaign:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return
    try {
      await campaignsApi.delete(id)
      fetchData()
    } catch (error) {
      console.error('Error deleting campaign:', error)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (campaign: Campaign) => (
        <div>
          <p className="font-medium text-secondary-900">{campaign.name}</p>
          <p className="text-sm text-secondary-500">{campaign.description}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (campaign: Campaign) => <StatusBadge status={campaign.status} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (campaign: Campaign) => new Date(campaign.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (campaign: Campaign) => (
        <div className="flex items-center space-x-2">
          {campaign.status === 'DRAFT' && (
            <>
              <button
                onClick={(e) => { e.stopPropagation(); handleStart(campaign.id); }}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                title="Start Campaign"
              >
                <Play className="h-4 w-4" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleDelete(campaign.id); }}
                className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                title="Delete"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </>
          )}
          {campaign.status === 'RUNNING' && (
            <button
              onClick={(e) => { e.stopPropagation(); handleStop(campaign.id); }}
              className="p-2 text-orange-600 hover:bg-orange-50 rounded-lg"
              title="Stop Campaign"
            >
              <Square className="h-4 w-4" />
            </button>
          )}
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
            <h1 className="text-2xl font-bold text-secondary-900">Campaigns</h1>
            <p className="text-secondary-500 mt-1">Manage phishing simulation campaigns</p>
          </div>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center">
            <Plus className="h-5 w-5 mr-2" />
            New Campaign
          </button>
        </div>

        <Table
          columns={columns}
          data={campaigns}
          keyExtractor={(c) => c.id}
          onRowClick={(c) => router.push(`/campaigns/${c.id}`)}
          emptyMessage="No campaigns yet. Create your first campaign!"
        />

        {/* Create Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create Campaign"
          size="lg"
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="label">Campaign Name</label>
              <input
                type="text"
                className="input"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Description</label>
              <textarea
                className="input"
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Email Template</label>
              <select
                className="input"
                value={formData.template_id}
                onChange={(e) => setFormData({ ...formData, template_id: e.target.value })}
              >
                <option value="">Select a template</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Target Users</label>
              <div className="max-h-48 overflow-y-auto border border-secondary-200 rounded-lg p-3 space-y-2">
                {users.filter(u => u.role === 'USER').map((user) => (
                  <label key={user.id} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.target_user_ids.includes(user.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({ ...formData, target_user_ids: [...formData.target_user_ids, user.id] })
                        } else {
                          setFormData({ ...formData, target_user_ids: formData.target_user_ids.filter(id => id !== user.id) })
                        }
                      }}
                      className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-secondary-700">{user.first_name} {user.last_name} ({user.email})</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex justify-end space-x-3 pt-4">
              <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create Campaign
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </Layout>
  )
}
