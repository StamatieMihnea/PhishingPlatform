'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import Table from '@/components/Table'
import Modal from '@/components/Modal'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { templatesApi } from '@/lib/api'
import { EmailTemplate } from '@/types'
import { Plus, Mail, Eye, Trash2, Edit } from 'lucide-react'

export default function TemplatesPage() {
  const router = useRouter()
  const { isAuthenticated } = useAuthStore()
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [preview, setPreview] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: '',
    subject: '',
    body_html: '',
    difficulty: 'MEDIUM' as 'EASY' | 'MEDIUM' | 'HARD',
    category: '',
  })

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    fetchTemplates()
  }, [isAuthenticated, router])

  const fetchTemplates = async () => {
    try {
      const data = await templatesApi.list()
      setTemplates(data.templates || [])
    } catch (error) {
      console.error('Error fetching templates:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await templatesApi.create(formData)
      setShowCreateModal(false)
      setFormData({ name: '', subject: '', body_html: '', difficulty: 'MEDIUM', category: '' })
      fetchTemplates()
    } catch (error) {
      console.error('Error creating template:', error)
    }
  }

  const handlePreview = async (id: string) => {
    try {
      const data = await templatesApi.preview(id)
      setPreview(data)
      setShowPreviewModal(true)
    } catch (error) {
      console.error('Error previewing template:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return
    try {
      await templatesApi.delete(id)
      fetchTemplates()
    } catch (error) {
      console.error('Error deleting template:', error)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Template',
      render: (template: EmailTemplate) => (
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            <Mail className="h-5 w-5 text-primary-600" />
          </div>
          <div>
            <p className="font-medium text-secondary-900">{template.name}</p>
            <p className="text-sm text-secondary-500">{template.subject}</p>
          </div>
        </div>
      ),
    },
    {
      key: 'difficulty',
      header: 'Difficulty',
      render: (template: EmailTemplate) => <StatusBadge status={template.difficulty} />,
    },
    {
      key: 'category',
      header: 'Category',
      render: (template: EmailTemplate) => template.category || '—',
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (template: EmailTemplate) => new Date(template.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (template: EmailTemplate) => (
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => { e.stopPropagation(); handlePreview(template.id); }}
            className="p-2 text-primary-600 hover:bg-primary-50 rounded-lg"
            title="Preview"
          >
            <Eye className="h-4 w-4" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleDelete(template.id); }}
            className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
            title="Delete"
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
            <h1 className="text-2xl font-bold text-secondary-900">Email Templates</h1>
            <p className="text-secondary-500 mt-1">Manage phishing email templates</p>
          </div>
          <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center">
            <Plus className="h-5 w-5 mr-2" />
            New Template
          </button>
        </div>

        <Table
          columns={columns}
          data={templates}
          keyExtractor={(t) => t.id}
          emptyMessage="No templates yet"
        />

        {/* Create Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create Email Template"
          size="xl"
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Template Name</label>
                <input
                  type="text"
                  className="input"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="label">Category</label>
                <input
                  type="text"
                  className="input"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  placeholder="e.g., Banking, IT Support"
                />
              </div>
            </div>
            <div>
              <label className="label">Email Subject</label>
              <input
                type="text"
                className="input"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Difficulty</label>
              <select
                className="input"
                value={formData.difficulty}
                onChange={(e) => setFormData({ ...formData, difficulty: e.target.value as any })}
              >
                <option value="EASY">Easy (obvious phishing)</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard (sophisticated)</option>
              </select>
            </div>
            <div>
              <label className="label">HTML Body</label>
              <textarea
                className="input font-mono text-sm"
                rows={12}
                value={formData.body_html}
                onChange={(e) => setFormData({ ...formData, body_html: e.target.value })}
                placeholder="<html>&#10;  <body>&#10;    <p>Dear {{ recipient_name }},</p>&#10;    <a href='{{ phishing_url }}{{ tracking_token }}'>Click here</a>&#10;  </body>&#10;</html>"
                required
              />
              <p className="text-xs text-secondary-500 mt-1">
                Available variables: {'{{ recipient_name }}'}, {'{{ recipient_email }}'}, {'{{ phishing_url }}'}, {'{{ tracking_token }}'}
              </p>
            </div>
            <div className="flex justify-end space-x-3 pt-4">
              <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create Template
              </button>
            </div>
          </form>
        </Modal>

        {/* Preview Modal */}
        <Modal
          isOpen={showPreviewModal}
          onClose={() => setShowPreviewModal(false)}
          title={`Preview: ${preview?.template_name}`}
          size="xl"
        >
          {preview && (
            <div className="space-y-4">
              <div className="p-4 bg-secondary-50 rounded-lg">
                <p className="text-sm text-secondary-500">Subject</p>
                <p className="font-medium text-secondary-900">{preview.subject}</p>
              </div>
              <div className="border border-secondary-200 rounded-lg overflow-hidden">
                <div className="p-2 bg-secondary-100 border-b border-secondary-200">
                  <p className="text-xs text-secondary-500">Email Preview</p>
                </div>
                <div
                  className="p-4 bg-white"
                  dangerouslySetInnerHTML={{ __html: preview.body_html }}
                />
              </div>
            </div>
          )}
        </Modal>
      </div>
    </Layout>
  )
}
