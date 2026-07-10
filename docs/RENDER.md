# Deploy on Render

## What you get

| Service | URL pattern |
|---------|-------------|
| Web UI | `https://eaw-web.onrender.com` (name may vary) |
| API | `https://eaw-api.onrender.com` |
| API docs | `https://eaw-api.onrender.com/docs` |
| Postgres | managed by Render |

Demo mode uses **hash embeddings + echo LLM** (no OpenAI key required).  
Upload/chat still work; answers are stubbed until you set `OPENAI_API_KEY`.

## Prerequisites

1. [GitHub](https://github.com) account  
2. [Render](https://render.com) account (sign up with GitHub)  
3. This repo pushed to GitHub  

## One-time: push to GitHub

From the project folder:

```powershell
cd $env:USERPROFILE\OneDrive\Desktop\enterprise-ai-workspace

# Login (browser)
gh auth login

# Create private repo + push
gh repo create enterprise-ai-workspace --private --source=. --remote=origin --push
```

If `git` is not initialized yet:

```powershell
git init
git add .
git commit -m "Initial commit — Enterprise AI Workspace for Render"
gh repo create enterprise-ai-workspace --private --source=. --remote=origin --push
```

## Deploy with Blueprint (recommended)

1. Open [https://dashboard.render.com](https://dashboard.render.com)  
2. **New → Blueprint**  
3. Connect the `enterprise-ai-workspace` GitHub repo  
4. Render reads `render.yaml` and proposes:
   - `eaw-db` (Postgres)
   - `eaw-api` (FastAPI)
   - `eaw-web` (Next.js)
5. Click **Apply**  
6. Wait for both services to go **Live** (first build can take 5–15 minutes)

### If free Postgres is unavailable

Create a **Postgres** instance on the starter plan, or use free [Neon](https://neon.tech) / [Supabase](https://supabase.com):

1. Copy the connection string  
2. In Render → `eaw-api` → Environment → set `DATABASE_URL`  
3. Redeploy `eaw-api`

## After deploy

1. Open the **eaw-web** URL  
2. Register a user → create a workspace → knowledge bases  
3. Optional: set env on `eaw-api`:
   - `LLM_PROVIDER=openai`
   - `EMBEDDING_PROVIDER=openai`
   - `OPENAI_API_KEY=sk-...`
   - Redeploy API  

## Free-tier notes

- Services **sleep** after ~15 minutes idle → first hit is slow  
- Disk is **ephemeral** (uploads in `/tmp` are lost on restart)  
- Vector store is **in-memory** (lost on restart; fine for demos)  
- For always-on + real vectors, upgrade plans and set `VECTOR_STORE_BACKEND=qdrant` + a Qdrant Cloud URL  

## Manual service setup (without Blueprint)

### API

- Root directory: `apps/api`  
- Build: `pip install -r requirements.txt`  
- Start: `bash start.sh`  
- Health: `/health`  
- Env: `DATABASE_URL`, `JWT_SECRET`, `APP_ENV=production`, `INGESTION_MODE=sync`, `VECTOR_STORE_BACKEND=memory`, `EMBEDDING_PROVIDER=hash`, `LLM_PROVIDER=echo`, `STORAGE_BACKEND=local`, `LOCAL_STORAGE_PATH=/tmp/eaw-uploads`, `CORS_ORIGINS=<web-url>`

### Web

- Root directory: `apps/web`  
- Build: `npm ci && npm run build`  
- Start: `npm run start -- --hostname 0.0.0.0 --port $PORT`  
- Env: `NEXT_PUBLIC_API_URL=<api-url>` (**must** be set **before** build, then rebuild)
