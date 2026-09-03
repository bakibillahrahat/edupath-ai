# 🌐 100% Free Cloud Deployment Guide for EduPath AI

This guide shows you how to deploy the entire EduPath AI system (Database, Redis, FastAPI Backend, and Streamlit Frontend) completely **free of cost**, with **no credit card required**.

---

## 🏛️ Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│ Streamlit Community Cloud (Frontend)                     │
│ URL: https://edupath-ai.streamlit.app                     │
└────────────────────────────┬─────────────────────────────┘
                             │ HTTPS API calls
                             ▼
┌──────────────────────────────────────────────────────────┐
│ Render / Koyeb (FastAPI Backend)                         │
│ URL: https://edupath-backend.onrender.com                │
└──────────────┬────────────────────────────┬──────────────┘
               │                            │
               ▼                            ▼
┌───────────────────────────────┐ ┌────────────────────────┐
│ Neon.tech (PostgreSQL+pgvector)│ │ Upstash (Serverless    │
│ 100% Free Database            │ │ Redis Cache)           │
└───────────────────────────────┘ └────────────────────────┘
```

---

## Step 1: Create Free PostgreSQL Database on Neon (2 Minutes)

1. Go to [https://neon.tech](https://neon.tech) and sign up with GitHub (No credit card needed).
2. Click **Create Project** (Name: `edupath-db`).
3. In the Neon Console, click **SQL Editor** and enable `pgvector`:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
4. Copy your connection string from the Dashboard. It looks like:
   ```text
   postgresql://alex:Abc123xyz@ep-fancy-pool-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Change `postgresql://` to `postgresql+asyncpg://` for SQLAlchemy:
   ```text
   postgresql+asyncpg://alex:Abc123xyz@ep-fancy-pool-123456.us-east-2.aws.neon.tech/neondb
   ```
   *(Save this as your `DATABASE_URL`)*.

---

## Step 2: Create Free Redis Cache on Upstash (1 Minute)

1. Go to [https://upstash.com](https://upstash.com) and sign up with GitHub.
2. Click **Create Database** (Type: **Redis**, Name: `edupath-redis`, Region: Pick same region as Neon, e.g., US-East).
3. Under **Connect to your database**, select **redis-py** / standard URL.
4. Copy the `rediss://...` connection string:
   ```text
   rediss://default:abc123token@us1-fancy-cat-12345.upstash.io:6379
   ```
   *(Save this as your `REDIS_URL`)*.

---

## Step 3: Deploy FastAPI Backend on Render (3 Minutes)

1. Push your code to a GitHub repository:
   ```bash
   git add .
   git commit -m "feat: deployment configurations"
   git push origin main
   ```
2. Go to [https://render.com](https://render.com) and sign in with GitHub.
3. Click **New +** -> **Web Service**.
4. Connect your `edupath-ai` GitHub repository.
5. Fill in the settings:
   - **Name**: `edupath-backend`
   - **Region**: Oregon or Ohio
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `alembic upgrade head && python scripts/seed_catalog.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
6. Scroll down to **Environment Variables** and add:
   | Key | Value |
   |---|---|
   | `DATABASE_URL` | *Your Neon asyncpg URL from Step 1* |
   | `REDIS_URL` | *Your Upstash URL from Step 2* |
   | `OPENROUTER_API_KEY` | `sk-or-v1-...` *(Your OpenRouter key)* |
   | `OPENROUTER_MODEL` | `minimax/minimax-m3:free` |
   | `JWT_SECRET_KEY` | `fNGp03D84fUtqmOLtfFKSAK1mrnBP-Uhq4qY2HZBQCPp0HIHh9RMydw1rwZK9YCw` |
   | `FRONTEND_URL` | `https://<your-app>.streamlit.app` |
7. Click **Deploy Web Service**.
8. Render will build and run database migrations automatically. Once ready, copy your backend URL:
   `https://edupath-backend.onrender.com`

---

## Step 4: Deploy Streamlit Frontend on Streamlit Community Cloud (2 Minutes)

1. Go to [https://share.streamlit.io](https://share.streamlit.io) and sign in with your GitHub account.
2. Click **Create app**.
3. Choose your repository: `username/edupath-ai`, Branch: `main`.
4. Set **Main file path**: `streamlit_app/app.py`.
5. Expand **Advanced settings...**:
   - In the **Secrets** text box, add:
     ```toml
     BACKEND_URL = "https://edupath-backend.onrender.com"
     ```
6. Click **Deploy!**
7. Within 1-2 minutes, your live Streamlit portal will be online with a public URL like:
   `https://edupath-ai.streamlit.app`

---

## ⚡ Local / VM Database Infrastructure

For running PostgreSQL with pgvector and Redis locally or on a VM:

```bash
docker compose -f infrastructure/docker/compose.yaml up -d
```
