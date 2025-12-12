'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/store'
import { keycloakLogout, getKeycloak } from '@/lib/keycloak'
import {
  LayoutDashboard,
  Building2,
  Users,
  Target,
  Mail,
  Shield,
  LogOut,
  Menu,
  X,
  ChevronDown,
  GraduationCap,
  KeyRound,
} from 'lucide-react'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout, authSource } = useAuthStore()

  const handleLogout = () => {
    // Logout from local state first
    logout()
    
    // If authenticated via Keycloak, also logout from Keycloak
    if (authSource === 'keycloak') {
      try {
        keycloakLogout(window.location.origin + '/login')
      } catch (e) {
        // Keycloak not available, just redirect
        router.push('/login')
      }
    } else {
      router.push('/login')
    }
  }

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: ['SUPER_ADMIN', 'ADMIN', 'USER'] },
    { name: 'Companies', href: '/companies', icon: Building2, roles: ['SUPER_ADMIN'] },
    { name: 'Users', href: '/users', icon: Users, roles: ['SUPER_ADMIN', 'ADMIN'] },
    { name: 'Campaigns', href: '/campaigns', icon: Target, roles: ['SUPER_ADMIN', 'ADMIN'] },
    { name: 'Templates', href: '/templates', icon: Mail, roles: ['SUPER_ADMIN', 'ADMIN'] },
    { name: 'My Results', href: '/my-results', icon: Shield, roles: ['USER'] },
    { name: 'Training', href: '/training', icon: GraduationCap, roles: ['USER'] },
  ]

  const filteredNavigation = navigation.filter(
    (item) => user && item.roles.includes(user.role)
  )

  return (
    <div className="min-h-screen bg-secondary-50">
      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-40 h-screen transition-transform ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } bg-white border-r border-secondary-200 w-64`}
      >
        <div className="h-full flex flex-col">
          {/* Logo */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-secondary-200">
            <Link href="/dashboard" className="flex items-center space-x-2">
              <Shield className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold text-secondary-900">PhishGuard</span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-secondary-500 hover:text-secondary-700"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
            {filteredNavigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900'
                  }`}
                >
                  <item.icon className={`h-5 w-5 mr-3 ${isActive ? 'text-primary-600' : 'text-secondary-400'}`} />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="border-t border-secondary-200 p-4">
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center w-full p-3 rounded-lg hover:bg-secondary-100 transition-colors"
              >
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                  <span className="text-primary-700 font-medium">
                    {user?.first_name?.charAt(0)}{user?.last_name?.charAt(0)}
                  </span>
                </div>
                <div className="ml-3 flex-1 text-left">
                  <p className="text-sm font-medium text-secondary-900">
                    {user?.first_name} {user?.last_name}
                  </p>
                  <div className="flex items-center space-x-1">
                    <p className="text-xs text-secondary-500">{user?.role}</p>
                    {authSource === 'keycloak' && (
                      <span title="SSO Authenticated">
                        <KeyRound className="h-3 w-3 text-blue-500" />
                      </span>
                    )}
                  </div>
                </div>
                <ChevronDown className="h-5 w-5 text-secondary-400" />
              </button>

              {userMenuOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-lg border border-secondary-200 py-1">
                  <div className="px-4 py-2 border-b border-secondary-100">
                    <p className="text-xs text-secondary-500">
                      {authSource === 'keycloak' ? 'SSO Authentication' : 'Local Authentication'}
                    </p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                  >
                    <LogOut className="h-4 w-4 mr-2" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className={`transition-all ${sidebarOpen ? 'lg:ml-64' : ''}`}>
        {/* Top bar */}
        <header className="bg-white border-b border-secondary-200 sticky top-0 z-30">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-secondary-500 hover:text-secondary-700"
            >
              <Menu className="h-6 w-6" />
            </button>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-secondary-500">
                {user?.email}
              </span>
              {authSource === 'keycloak' && (
                <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full flex items-center">
                  <KeyRound className="h-3 w-3 mr-1" />
                  SSO
                </span>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
