'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Layout from '@/components/Layout'
import Table from '@/components/Table'
import Modal from '@/components/Modal'
import { StatusBadge } from '@/components/Badge'
import { useAuthStore } from '@/lib/store'
import { usersApi, companiesApi } from '@/lib/api'
import { User, Company } from '@/types'
import { Plus, Upload, Trash2, UserCheck, UserX, Building2 } from 'lucide-react'

export default function UsersPage() {
  const router = useRouter()
  const { isAuthenticated, user: currentUser } = useAuthStore()
  const [users, setUsers] = useState<User[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showImportModal, setShowImportModal] = useState(false)
  const [selectedCompanyFilter, setSelectedCompanyFilter] = useState<string>('')
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    password: '',
    role: 'USER' as 'ADMIN' | 'USER',
    company_id: '',
  })
  const [csvData, setCsvData] = useState('')
  const [importCompanyId, setImportCompanyId] = useState('')

  const isSuperAdmin = currentUser?.role === 'SUPER_ADMIN'

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login')
      return
    }
    fetchUsers()
    if (isSuperAdmin) {
      fetchCompanies()
    }
  }, [isAuthenticated, router, isSuperAdmin])

  const fetchCompanies = async () => {
    try {
      const data = await companiesApi.list()
      setCompanies(data.companies || [])
    } catch (error) {
      console.error('Error fetching companies:', error)
    }
  }

  const fetchUsers = async (companyId?: string) => {
    try {
      const data = await usersApi.list(1, 100, companyId)
      setUsers(data.users || [])
    } catch (error) {
      console.error('Error fetching users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCompanyFilterChange = (companyId: string) => {
    setSelectedCompanyFilter(companyId)
    fetchUsers(companyId || undefined)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const dataToSend = { ...formData }
      // For non-super-admins, company_id is set by the backend
      if (!isSuperAdmin) {
        delete (dataToSend as any).company_id
      } else if (!dataToSend.company_id) {
        alert('Please select a company for the user')
        return
      }
      await usersApi.create(dataToSend)
      setShowCreateModal(false)
      setFormData({ email: '', first_name: '', last_name: '', password: '', role: 'USER', company_id: '' })
      fetchUsers(selectedCompanyFilter || undefined)
    } catch (error) {
      console.error('Error creating user:', error)
    }
  }

  const handleImport = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isSuperAdmin && !importCompanyId) {
      alert('Please select a company for the imported users')
      return
    }
    try {
      const result = await usersApi.import(csvData, isSuperAdmin ? importCompanyId : undefined)
      alert(`Imported: ${result.imported}, Failed: ${result.failed}`)
      setShowImportModal(false)
      setCsvData('')
      setImportCompanyId('')
      fetchUsers(selectedCompanyFilter || undefined)
    } catch (error) {
      console.error('Error importing users:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to deactivate this user?')) return
    try {
      await usersApi.delete(id)
      fetchUsers()
    } catch (error) {
      console.error('Error deleting user:', error)
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Name',
      render: (user: User) => (
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
            <span className="text-primary-700 font-medium">
              {user.first_name.charAt(0)}{user.last_name.charAt(0)}
            </span>
          </div>
          <div>
            <p className="font-medium text-secondary-900">{user.first_name} {user.last_name}</p>
            <p className="text-sm text-secondary-500">{user.email}</p>
          </div>
        </div>
      ),
    },
    ...(isSuperAdmin ? [{
      key: 'company',
      header: 'Company',
      render: (user: User) => (
        <div className="flex items-center space-x-2">
          <Building2 className="h-4 w-4 text-secondary-400" />
          <span className="text-secondary-700">{user.company_name || 'No company'}</span>
        </div>
      ),
    }] : []),
    {
      key: 'role',
      header: 'Role',
      render: (user: User) => <StatusBadge status={user.role} />,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (user: User) => (
        <span className={`flex items-center ${user.is_active ? 'text-green-600' : 'text-red-600'}`}>
          {user.is_active ? <UserCheck className="h-4 w-4 mr-1" /> : <UserX className="h-4 w-4 mr-1" />}
          {user.is_active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (user: User) => new Date(user.created_at).toLocaleDateString(),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (user: User) => (
        <button
          onClick={(e) => { e.stopPropagation(); handleDelete(user.id); }}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
          title="Deactivate"
        >
          <Trash2 className="h-4 w-4" />
        </button>
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
            <h1 className="text-2xl font-bold text-secondary-900">Users</h1>
            <p className="text-secondary-500 mt-1">Manage company users</p>
          </div>
          <div className="flex items-center space-x-3">
            {isSuperAdmin && (
              <select
                className="input w-48"
                value={selectedCompanyFilter}
                onChange={(e) => handleCompanyFilterChange(e.target.value)}
              >
                <option value="">All Companies</option>
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
            )}
            <button onClick={() => setShowImportModal(true)} className="btn-secondary flex items-center">
              <Upload className="h-5 w-5 mr-2" />
              Import CSV
            </button>
            <button onClick={() => setShowCreateModal(true)} className="btn-primary flex items-center">
              <Plus className="h-5 w-5 mr-2" />
              Add User
            </button>
          </div>
        </div>

        <Table
          columns={columns}
          data={users}
          keyExtractor={(u) => u.id}
          emptyMessage="No users yet"
        />

        {/* Create Modal */}
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Add New User"
        >
          <form onSubmit={handleCreate} className="space-y-4">
            {isSuperAdmin && (
              <div>
                <label className="label">Company *</label>
                <select
                  className="input"
                  value={formData.company_id}
                  onChange={(e) => setFormData({ ...formData, company_id: e.target.value })}
                  required
                >
                  <option value="">Select a company</option>
                  {companies.map((company) => (
                    <option key={company.id} value={company.id}>{company.name}</option>
                  ))}
                </select>
                <p className="text-xs text-secondary-500 mt-1">Select which company this user belongs to</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">First Name</label>
                <input
                  type="text"
                  className="input"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="label">Last Name</label>
                <input
                  type="text"
                  className="input"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                minLength={8}
              />
              <p className="text-xs text-secondary-500 mt-1">Min 8 characters, 1 uppercase, 1 lowercase, 1 digit</p>
            </div>
            <div>
              <label className="label">Role</label>
              <select
                className="input"
                value={formData.role}
                onChange={(e) => setFormData({ ...formData, role: e.target.value as 'ADMIN' | 'USER' })}
              >
                <option value="USER">User</option>
                {currentUser?.role === 'SUPER_ADMIN' && <option value="ADMIN">Admin</option>}
              </select>
            </div>
            <div className="flex justify-end space-x-3 pt-4">
              <button type="button" onClick={() => setShowCreateModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Create User
              </button>
            </div>
          </form>
        </Modal>

        {/* Import Modal */}
        <Modal
          isOpen={showImportModal}
          onClose={() => setShowImportModal(false)}
          title="Import Users from CSV"
        >
          <form onSubmit={handleImport} className="space-y-4">
            {isSuperAdmin && (
              <div>
                <label className="label">Company *</label>
                <select
                  className="input"
                  value={importCompanyId}
                  onChange={(e) => setImportCompanyId(e.target.value)}
                  required
                >
                  <option value="">Select a company</option>
                  {companies.map((company) => (
                    <option key={company.id} value={company.id}>{company.name}</option>
                  ))}
                </select>
                <p className="text-xs text-secondary-500 mt-1">All imported users will be assigned to this company</p>
              </div>
            )}
            <div>
              <label className="label">CSV Data</label>
              <textarea
                className="input font-mono text-sm"
                rows={10}
                value={csvData}
                onChange={(e) => setCsvData(e.target.value)}
                placeholder="email,first_name,last_name,password&#10;john@example.com,John,Doe,Password123!"
                required
              />
              <p className="text-xs text-secondary-500 mt-1">
                Format: email,first_name,last_name,password (password is optional)
              </p>
            </div>
            <div className="flex justify-end space-x-3 pt-4">
              <button type="button" onClick={() => setShowImportModal(false)} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Import Users
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </Layout>
  )
}
