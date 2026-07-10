# Deploy free on **Vercel** (no Render, no paid DB)

Hobby plan is free. No credit card required for normal hobby use.

You deploy **two projects** from the same GitHub repo:

| Project | Root directory | URL |
|---------|----------------|-----|
| API | `apps/api` | `https://eaw-api-….vercel.app` |
| Web | `apps/web` | `https://eaw-web-….vercel.app` |

Database: **SQLite on `/tmp`** (free). Data may reset when serverless instances recycle — fine for demos.

---

## 1. Sign up

1. Open https://vercel.com/signup  
2. Continue with **GitHub** (Aman05cody)  
3. Import is free

---

## 2. Deploy the API

1. Vercel → **Add New… → Project**  
2. Import **`enterprise-AI-Workspace`**  
3. **Root Directory** → **Edit** → choose **`apps/api`**  
4. Framework: Other / leave default  
5. **Environment Variables** (Production):

| Name | Value |
|------|--------|
| `JWT_SECRET` | any long random string (32+ chars) |
| `DATABASE_URL` | `sqlite:////tmp/eaw.db` |
| `APP_ENV` | `production` |
| `INGESTION_MODE` | `sync` |
| `EMBEDDING_PROVIDER` | `hash` |
| `VECTOR_STORE_BACKEND` | `memory` |
| `LLM_PROVIDER` | `echo` |
| `STORAGE_BACKEND` | `local` |
| `LOCAL_STORAGE_PATH` | `/tmp/eaw-uploads` |
| `CORS_ORIGINS` | `https://localhost` *(update after web deploys)* |

6. **Install Command:**  
   `pip install -r requirements-vercel.txt`  
   (or leave blank if using default; if install fails, set this in Project Settings → Build & Development)

7. Click **Deploy**  
8. Copy the API URL, e.g. `https://enterprise-ai-workspace-api.vercel.app`

Check: `https://YOUR-API.vercel.app/health` → `{"status":"ok"}`  
Docs: `https://YOUR-API.vercel.app/docs`

> If build looks for `requirements.txt` only, either rename or set Install Command to use `requirements-vercel.txt`.

---

## 3. Deploy the Web

1. **Add New… → Project** again (same repo)  
2. Root Directory → **`apps/web`**  
3. Framework Preset: **Next.js**  
4. Environment Variables:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-API.vercel.app` *(no trailing slash)* |

5. **Deploy**  
6. Copy the web URL

---

## 4. Wire CORS (1 minute)

1. Open API project → Settings → Environment Variables  
2. Set `CORS_ORIGINS` = your web URL, e.g. `https://eaw-web.vercel.app`  
3. Also set `WEB_URL` to the same  
4. **Redeploy** the API (Deployments → … → Redeploy)

---

## 5. Use the app

Open the **web** URL → Register → create workspace.

---

## Optional: free persistent DB (still $0)

If you want data to survive cold starts:

1. https://neon.tech → free project  
2. Copy connection string  
3. API env: `DATABASE_URL=postgresql://…?sslmode=require`  
4. From your PC (with venv):

```powershell
cd apps\api
$env:DATABASE_URL="postgresql+psycopg://…your neon url…"
$env:PYTHONPATH="src"
.\.venv\Scripts\alembic.exe upgrade head
```

5. Redeploy API  

Neon free tier does **not** require paying Render-style Postgres.

---

## CLI alternative

```powershell
npm i -g vercel
vercel login

cd apps\api
vercel --prod

cd ..\web
vercel --prod
```

Set env vars when prompted or in the dashboard.

---

## Honest limits

- Free serverless: cold starts, execution time limits  
- SQLite `/tmp` is demo-grade  
- Heavy connector sync jobs are not ideal on serverless  
- Perfect for **portfolio / demo / interview**
