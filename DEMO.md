# Live demo — Enterprise AI Workspace

Public demo hosted on **Vercel** (free hobby tier).

## Links

| Service | URL |
|---------|-----|
| **Frontend (use this)** | https://eaw-web.vercel.app |
| Backend API | https://eaw-api.vercel.app |
| Swagger / OpenAPI | https://eaw-api.vercel.app/docs |
| Health | https://eaw-api.vercel.app/health |

## How to try

1. Open **https://eaw-web.vercel.app**
2. Click **Get started** / **Register**
3. Use any email + password (min 8 characters, include letters **and** numbers, e.g. `Demo1234`)
4. Create a workspace on the dashboard
5. Explore Knowledge, Chat, Connectors, Analytics

## What works in the demo

- Multi-tenant auth (register / login / JWT)
- Workspaces + RBAC roles
- Knowledge bases & document upload (demo storage)
- Grounded chat pipeline (demo **echo** LLM + **hash** embeddings)
- Connector UIs (GitHub, Notion, Drive, Slack, Jira)
- Admin analytics UI

## Limits (honest)

- Serverless cold starts → first request may take a few seconds
- SQLite on ephemeral `/tmp` → accounts/data can reset after idle/redeploy
- Not a paid production SLA — portfolio / interview demo

## Source code

https://github.com/Aman05cody/enterprise-AI-Workspace

Local run: see [README.md](./README.md).  
Redeploy guide: [docs/VERCEL.md](./docs/VERCEL.md).
