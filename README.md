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

Import this repository in Vercel. Set Root Directory to `frontend`. Keep the detected Vite settings: build command `npm run build`, output directory `dist`. Deploy. Paste the Vercel URL into `DEPLOYED_URL` and into `ALLOWED_ORIGINS` on Render.

`frontend/vercel.json` rewrites `/api/:path*` to `https://wind-forecast-74xc.onrender.com/api/:path*`. The browser still calls the relative path `/api`. No Vercel environment variable is required for that rewrite.

# Assumptions

# AI disclosure

# Video
