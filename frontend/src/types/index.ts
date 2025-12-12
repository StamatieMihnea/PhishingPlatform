export interface Company {
  id: string
  name: string
  domain: string
  logo_url?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'SUPER_ADMIN' | 'ADMIN' | 'USER'
  company_id?: string
  company_name?: string
  is_active: boolean
  last_login?: string
  created_at: string
}

export interface Campaign {
  id: string
  company_id: string
  created_by: string
  name: string
  description?: string
  template_id?: string
  phishing_url?: string
  status: 'DRAFT' | 'SCHEDULED' | 'RUNNING' | 'COMPLETED'
  scheduled_at?: string
  started_at?: string
  completed_at?: string
  created_at: string
  updated_at: string
}

export interface EmailTemplate {
  id: string
  company_id?: string
  name: string
  subject: string
  body_html: string
  difficulty: 'EASY' | 'MEDIUM' | 'HARD'
  category?: string
  created_at: string
  updated_at: string
}

export interface CampaignTarget {
  id: string
  campaign_id: string
  user_id: string
  user_email?: string
  user_name?: string
  email_sent: boolean
  email_sent_at?: string
  email_opened: boolean
  email_opened_at?: string
  link_clicked: boolean
  link_clicked_at?: string
  credentials_submitted: boolean
  submitted_at?: string
  created_at: string
}

export interface CampaignStats {
  campaign_id: string
  campaign_name: string
  status: string
  total_targets: number
  emails_sent: number
  emails_opened: number
  links_clicked: number
  credentials_submitted: number
  open_rate: number
  click_rate: number
  submission_rate: number
}

export interface CompanyStats {
  company_id: string
  company_name: string
  total_users: number
  total_campaigns: number
  total_emails_sent: number
  total_emails_opened: number
  total_links_clicked: number
  total_credentials_submitted: number
  click_rate: number
  submission_rate: number
}

export interface DashboardStats {
  total_campaigns: number
  campaigns_passed: number
  campaigns_failed: number
  success_rate: number
}

export interface Recommendation {
  id: string
  title: string
  description: string
  category: string
  priority: 'LOW' | 'MEDIUM' | 'HIGH'
}
