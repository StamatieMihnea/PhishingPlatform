# PhishingPlatform

**Student:** Stamatie Mihnea-Stefan  
**Group:** 343C3  

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Keycloak SSO](#keycloak-sso)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Configuration](#configuration)
- [Security](#security)

## Overview

PhishingPlatform enables organizations to:
- Conduct phishing simulation campaigns for employee training
- Track user interactions (email opens, link clicks, credential submissions)
- Generate detailed statistics and security recommendations
- Manage multiple companies with role-based access control
- **Single Sign-On (SSO) authentication via Keycloak**

### Key Technical Features

- **Microservices Architecture** with Docker Swarm orchestration
- **Keycloak SSO Integration** for OAuth 2.0 / OpenID Connect authentication
- **Multi-tenancy** with isolated company data
- **Asynchronous Email Processing** via RabbitMQ
- **Replicated Services** for high availability and load balancing

## Architecture

### System Components (8 Docker Containers)

| Container | Technology | Role | Type |
|-----------|------------|------|------|
| postgres | PostgreSQL 15 | Application database | Open-source |
| keycloak-db | PostgreSQL 15 | Keycloak database | Open-source |
| keycloak | Keycloak 23.0 | SSO / Identity Provider | Open-source |
| rabbitmq | RabbitMQ 3.12 | Message broker for async email tasks | Open-source |
| nginx | Nginx 1.25 | Reverse proxy & load balancer | Open-source |
| backend-api | FastAPI (Python) | REST API (replicated x2) | Developed |
| mail-scheduler | Python | Email queue processing (replicated x2) | Developed |
| frontend | Next.js + React | User interface | Developed |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Docker Swarm Cluster                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│    [Client Browser]                                                  │
│          │                                                           │
│          ▼                                                           │
│    ┌──────────┐                                                      │
│    │  NGINX   │ ◄── Port 80/443 (load balancer)                     │
│    │ (proxy)  │                                                      │
│    └────┬─────┘                                                      │
│         │                                                            │
│    ┌────┴─────────────────────┬──────────────────┐                  │
│    │                          │                  │                   │
│    ▼                          ▼                  ▼                   │
│ ┌──────────────┐    ┌─────────────────┐   ┌───────────┐             │
│ │   Frontend   │    │   Backend API   │   │ Keycloak  │             │
│ │  (Next.js)   │    │    (FastAPI)    │   │   (SSO)   │             │
│ └──────────────┘    │   Replicated x2 │   └─────┬─────┘             │
│                     └────────┬────────┘         │                    │
│                              │                  │                    │
│         ┌────────────────────┼──────────────────┘                   │
│         │                    │                                       │
│         ▼                    ▼                                       │
│   ┌─────────────┐     ┌─────────────┐   ┌─────────────┐             │
│   │ PostgreSQL  │     │  RabbitMQ   │   │ Keycloak DB │             │
│   │    (DB)     │     │   (Queue)   │   │ (PostgreSQL)│             │
│   └─────────────┘     └──────┬──────┘   └─────────────┘             │
│                              │                                       │
│                              ▼                                       │
│                       ┌──────────────┐                               │
│                       │    Mail      │                               │
│                       │  Scheduler   │ ◄── Replicated x2            │
│                       └──────┬───────┘                               │
│                              │                                       │
│                              ▼                                       │
│                       [SMTP Server]                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Network Security

| Network | Services | Purpose |
|---------|----------|---------|
| frontend-net | nginx, frontend, keycloak | Public access |
| backend-net | nginx, backend-api, frontend, keycloak | Internal API communication |
| data-net | backend-api, postgres | Database access (isolated) |
| queue-net | backend-api, rabbitmq, mail-scheduler | Async communication |
| keycloak-net | keycloak, keycloak-db | Keycloak database (isolated) |

## Features

### Authentication (Keycloak SSO)

The platform uses **Keycloak** for Single Sign-On (SSO) authentication:
- OAuth 2.0 / OpenID Connect protocol
- PKCE (Proof Key for Code Exchange) for secure authentication
- Role-based access control via Keycloak roles
- Multi-company support via custom user attributes

### User Roles

| Role | Level | Permissions |
|------|-------|-------------|
| SUPER_ADMIN | Platform | Manage companies, global stats, super admins |
| ADMIN | Company | Manage campaigns, users, templates, company stats |
| USER | Company | View own results, recommendations, training materials |

### Core Functionality

- **Campaign Management**: Create, schedule, start, stop phishing campaigns
- **Email Templates**: Customizable phishing email templates with difficulty levels
- **Tracking System**: Track email opens (pixel), link clicks, credential submissions
- **User Dashboard**: Personal statistics and security recommendations
- **Training Materials**: Security awareness training modules

## Prerequisites

- Docker 20.10+ with Swarm support (`docker swarm init`)

## Quick Start (Swarm only)

1) Clone and prepare environment
```bash
cd PhishingPlatform
cp env.example .env   # fill in if you have real SMTP / public URL
```

2) Build images
```bash
docker-compose build
```

3) Initialize Swarm (once on manager node)
```bash
docker swarm init
```

4) Deploy the stack
```bash
docker stack deploy -c docker-compose.yml phishing
```

5) Check status
```bash
docker stack services phishing
# all services should show REPLICAS X/X
```

6) Quick access
| Service | URL | Notes |
|---------|-----|-------|
| Frontend (app) | http://localhost | App UI |
| Keycloak (SSO via nginx) | http://localhost/auth | SSO login |
| Mailpit (test SMTP) | http://localhost:8025 | Test inbox |
| RabbitMQ Mgmt | http://localhost:15672 | guest/guest |

7) Remove stack
```bash
docker stack rm phishing
```

## Keycloak SSO

### Default Credentials (SSO)

- **Super Admin**: `superadmin@phishingplatform.com` / `SuperAdmin123!`
- **Admin (Demo Company)**: `admin@demo.com` / `Admin123!`
- **Users (Demo Company)**: `user1@demo.com` / `User123!`, `user2@demo.com` / `User123!`

Keycloak Admin Console (if needed): http://localhost/auth/ (admin/admin)

### Keycloak Configuration

The platform automatically imports a pre-configured Keycloak realm with:

- **Realm**: `phishing-platform`
- **Frontend Client**: `phishing-frontend` (public client with PKCE)
- **Backend Client**: `phishing-api` (confidential client, bearer-only)
- **Roles**: SUPER_ADMIN, ADMIN, USER
- **Custom Attributes**: `company_id` for multi-tenancy

### Manual Keycloak Setup (if needed)

1. Access Keycloak Admin Console: http://localhost:8080
2. Login with admin/admin
3. Import realm from `keycloak/realm-export.json` or create manually:
   - Create realm "phishing-platform"
   - Create roles: SUPER_ADMIN, ADMIN, USER
   - Create frontend client (public, PKCE enabled)
   - Create backend client (bearer-only)
   - Add users with appropriate roles

### How SSO Works

1. User clicks "Sign in with SSO" on login page
2. User is redirected to Keycloak login page
3. After successful authentication, Keycloak redirects back with authorization code
4. Frontend exchanges code for tokens using PKCE
5. Access token is sent with each API request
6. Backend validates token against Keycloak's JWKS endpoint

## Deployment (Docker Swarm)

### Deploy & Operate (Swarm)

- Initialize Swarm: `docker swarm init`
- Build images: `docker-compose build`
- Deploy: `docker stack deploy -c docker-compose.yml phishing`
- Status: `docker stack services phishing`
- Scale (example): `docker service scale phishing_backend-api=4`

##  API Documentation

### Authentication

| Endpoint | Method | Description | Access |
|----------|--------|-------------|--------|
| /api/v1/auth/login | POST | Legacy email/password login | Public |
| /api/v1/auth/logout | POST | Logout (returns Keycloak logout URL) | Authenticated |
| /api/v1/auth/refresh | POST | Refresh token | Authenticated |
| /api/v1/auth/me | GET | Current user info | Authenticated |
| /api/v1/auth/keycloak/config | GET | Keycloak configuration | Public |
| /api/v1/auth/keycloak/token | POST | Exchange Keycloak code for tokens | Public |

### Companies (Super Admin)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/companies | GET | List all companies |
| /api/v1/companies | POST | Create company |
| /api/v1/companies/{id} | GET | Get company details |
| /api/v1/companies/{id}/stats | GET | Get company statistics |

### Campaigns (Admin)

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/campaigns | GET | List campaigns |
| /api/v1/campaigns | POST | Create campaign |
| /api/v1/campaigns/{id}/schedule | POST | Schedule campaign |
| /api/v1/campaigns/{id}/start | POST | Start immediately |
| /api/v1/campaigns/{id}/stop | POST | Stop campaign |
| /api/v1/campaigns/{id}/stats | GET | Campaign statistics |

### User Dashboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/dashboard/my-campaigns | GET | My campaigns |
| /api/v1/dashboard/my-results | GET | My phishing test results |
| /api/v1/dashboard/recommendations | GET | Security recommendations |
| /api/v1/dashboard/training | GET | Training materials |

Full API documentation available at `/api/docs` (Swagger UI) or `/api/redoc` (ReDoc).

## Testing (dev/local)
- For end-to-end verification in Swarm:
  - SSO login as Super Admin.
  - Create a new company.
  - As Admin (e.g., `admin@demo.com`), create a campaign, add targets (user1/user2), start the campaign.
  - Check emails in Mailpit (http://localhost:8025) and tracking (open/click).

## Configuration

### Environment Variables

```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_USER=phishing_user
POSTGRES_PASSWORD=phishing_password

# Keycloak
KEYCLOAK_SERVER_URL=http://keycloak:8080
KEYCLOAK_REALM=phishing-platform
KEYCLOAK_CLIENT_ID=phishing-api
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_FROM_EMAIL=noreply@example.com
```

## Security

### Implemented Security Measures

- **Authentication**: Keycloak SSO with OAuth 2.0 / OIDC
- **Authorization**: Role-based access control (RBAC) via Keycloak roles
- **PKCE**: Proof Key for Code Exchange for secure token exchange
- **Multi-tenancy**: Strict data isolation between companies
- **Password Security**: Managed by Keycloak (bcrypt hashing)
- **Rate Limiting**: Protection against brute-force attacks
- **Input Validation**: Pydantic schemas for all inputs
- **SQL Injection**: SQLAlchemy ORM with parameterized queries
- **Network Isolation**: Docker networks for service separation

### Production Recommendations

1. Enable HTTPS with valid SSL certificates
2. Configure Keycloak with production database
3. Use strong passwords for all services
4. Enable Keycloak brute force detection
5. Set up monitoring and alerting
6. Regular security audits
7. Database backups

## Project Structure

```
PhishingPlatform/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── core/           # Config, security, keycloak, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   └── utils/          # Utilities
│   ├── tests/              # Backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── mail-scheduler/          # Email Worker Service
│   ├── app/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Next.js Frontend
│   ├── src/
│   │   ├── app/            # Pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client, store, keycloak
│   │   └── types/          # TypeScript types
│   ├── Dockerfile
│   └── package.json
├── keycloak/                # Keycloak Configuration
│   └── realm-export.json   # Pre-configured realm
├── nginx/                   # Nginx Configuration
│   ├── nginx.conf
│   └── ssl/
├── docker-compose.yml       # Production Swarm config
├── docker-compose.dev.yml   # Development config
└── README.md
```


**Author:** Stamatie Mihnea-Stefan  

