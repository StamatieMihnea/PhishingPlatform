'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Shield, Mail, Lock, AlertCircle, KeyRound } from 'lucide-react'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/lib/store'
import { 
  initKeycloak, 
  keycloakLogin, 
  getKeycloak, 
  getUserInfo, 
  getTokens,
  getPrimaryRole 
} from '@/lib/keycloak'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { setAuth, setKeycloakAuth, isAuthenticated } = useAuthStore()
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [keycloakReady, setKeycloakReady] = useState(false)
  const [checkingAuth, setCheckingAuth] = useState(true)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  // Initialize Keycloak and check existing authentication
  useEffect(() => {
    const init = async () => {
      try {
        const authenticated = await initKeycloak()
        setKeycloakReady(true)
        
        if (authenticated) {
          // User is already authenticated via Keycloak
          const userInfo = getUserInfo()
          const tokens = getTokens()
          
          if (userInfo && tokens) {
            setKeycloakAuth(
              {
                id: userInfo.sub,
                email: userInfo.email,
                first_name: userInfo.given_name,
                last_name: userInfo.family_name,
                role: getPrimaryRole(userInfo.roles),
                company_id: userInfo.company_id,
                is_active: true,
                auth_source: 'keycloak',
              },
              tokens.accessToken,
              tokens.refreshToken
            )
            router.push('/dashboard')
            return
          }
        }
      } catch (err) {
        console.error('Keycloak init error:', err)
      } finally {
        setCheckingAuth(false)
      }
    }

    init()
  }, [router, setKeycloakAuth])

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !checkingAuth) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, checkingAuth, router])

  // Handle Keycloak SSO login
  const handleKeycloakLogin = () => {
    setIsLoading(true)
    keycloakLogin(window.location.origin + '/dashboard')
  }

  // Handle legacy email/password login
  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    setError('')

    try {
      const response = await authApi.login(data.email, data.password)
      const { access_token, refresh_token } = response

      // Get user info
      localStorage.setItem('access_token', access_token)
      const user = await authApi.me()

      setAuth(
        {
          id: user.id,
          email: user.email,
          first_name: user.first_name,
          last_name: user.last_name,
          role: user.role,
          company_id: user.company_id,
          is_active: user.is_active,
          auth_source: 'database',
        },
        access_token,
        refresh_token,
        'legacy'
      )
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white rounded-2xl shadow-lg mb-4">
            <Shield className="h-10 w-10 text-primary-600" />
          </div>
          <h1 className="text-3xl font-bold text-white">PhishGuard</h1>
          <p className="text-primary-200 mt-2">Security Awareness Platform</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-2xl font-bold text-secondary-900 mb-6">Sign in</h2>

          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center text-red-700">
              <AlertCircle className="h-5 w-5 mr-2 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Keycloak SSO Login Button */}
          <button
            onClick={handleKeycloakLogin}
            disabled={isLoading || !keycloakReady}
            className="w-full mb-6 flex items-center justify-center px-4 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <KeyRound className="h-5 w-5 mr-2" />
            Sign in with SSO (Keycloak)
          </button>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-secondary-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-secondary-500">Or continue with email</span>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label htmlFor="email" className="label">
                Email address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                <input
                  {...register('email')}
                  type="email"
                  id="email"
                  className="input pl-10"
                  placeholder="you@company.com"
                />
              </div>
              {errors.email && <p className="error-text">{errors.email.message}</p>}
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-secondary-400" />
                <input
                  {...register('password')}
                  type="password"
                  id="password"
                  className="input pl-10"
                  placeholder="••••••••"
                />
              </div>
              {errors.password && <p className="error-text">{errors.password.message}</p>}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full py-3"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Signing in...
                </span>
              ) : (
                'Sign in with Email'
              )}
            </button>
          </form>

          {/* Demo credentials */}
          <div className="mt-6 p-4 bg-secondary-50 rounded-lg">
            <p className="text-sm font-medium text-secondary-700 mb-2">Demo Credentials (Keycloak SSO):</p>
            <div className="text-xs text-secondary-600 space-y-1">
              <p><strong>Super Admin:</strong> superadmin / SuperAdmin123!</p>
              <p><strong>Admin:</strong> admin@demo.com / Admin123!</p>
              <p><strong>User:</strong> user1@demo.com / User123!</p>
            </div>
            <p className="text-xs text-secondary-500 mt-2">
              <strong>Keycloak Admin Console:</strong> http://localhost:8080 (admin/admin)
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
