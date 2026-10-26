# Overview

# Directory structure

# How to run (Docker and non-Docker)

From a clone of this repository:

```
docker compose up --build
```

Open http://localhost:8080

# Re-running ingestion

# Deployed app

Import this repository in Vercel. Set Root Directory to `frontend`. Keep the detected Vite settings: build command `npm run build`, output directory `dist`. Add the environment variable `BACKEND_URL` with the value `url` and no trailing slash. Deploy. Paste the Vercel URL into `DEPLOYED_URL` and into `ALLOWED_ORIGINS` on Render.

`frontend/vercel.json` sends `/api/...` to `${BACKEND_URL}/api/...`. The browser still calls the relative path `/api`.

# Assumptions

# AI disclosure

# Video
