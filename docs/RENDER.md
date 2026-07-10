# Deploy on Render — **100% free**

No paid Postgres. Free web services + **SQLite** on the API.

| Service | Plan | Cost |
|---------|------|------|
| `eaw-api` | free | $0 |
| `eaw-web` | free | $0 |
| Database | SQLite file on API | $0 |

## Trade-offs (honest)

- Free services **sleep** after ~15 min idle → first open is slow  
- SQLite lives on ephemeral disk → **users/data reset** when the free API restarts/redeploys  
- Fine for demos/portfolio; not for real multi-user production data  

Optional later (still free): [Neon](https://neon.tech) free Postgres → set `DATABASE_URL` on `eaw-api`.

## Deploy steps

1. Repo must be on GitHub (yours: `Aman05cody/enterprise-AI-Workspace`)
2. [dashboard.render.com](https://dashboard.render.com) → sign in with GitHub  
3. **New → Blueprint** → select the repo  
4. Confirm **no paid database** is listed (only `eaw-api` + `eaw-web`)  
5. **Apply**  
6. Wait until both are **Live**  
7. Open the `eaw-web` URL  

## After deploy

- Register a user on the public site  
- API docs: `https://eaw-api-….onrender.com/docs`  
- Optional real AI: set `LLM_PROVIDER=openai`, `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY=…` on `eaw-api` (OpenAI usage is separate from Render)
