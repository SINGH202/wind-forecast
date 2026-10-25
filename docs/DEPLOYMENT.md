# Deployment

The live app is a static frontend on Vercel and a Docker API on Render. The browser never calls Elexon. January 2026 wind data is the committed `data/*.parquet` snapshot.

## Request path

The browser loads the Vite build from Vercel. Every API call uses the relative path `/api/...`. In production, Vercel rewrites `/api/*` to the Render service. Render runs the FastAPI process and reads the parquet files inside the image. Nothing in that path calls Elexon.

Locally, the same `/api` path is proxied by Vite. Source code does not contain `localhost` or the Render host.

## What runs where

| Piece | Host | Role |
| --- | --- | --- |
| Static frontend | Vercel | Built HTML, CSS, and JavaScript |
| Backend | Render | Docker web service, FastAPI |
| Snapshot | Inside the backend image | `data/*.parquet`, read at runtime |

The frontend and the API are separate deploys. The only link is the rewrite from `/api/*` on the Vercel host to Render.

## Why this split

The frontend is a static Vite build, so Vercel can serve it. The API is a Docker image, so it runs on Render. This repo does not treat "Vercel cannot run Docker containers" as a checked fact: **UNVERIFIED**. Confirm that in the current Vercel docs before relying on it.

## How the snapshot gets into the image

`data/*.parquet` is committed. The backend image is built with the repository root as its Docker context, not `backend/` alone, so the build can copy `data/` into the image. At runtime the API reads those files. It does not download a fresh copy and it does not call Elexon. No secrets belong in the image or the repo. The backend reads `PORT` (default 8000) and `ALLOWED_ORIGINS` from the environment.

## Things to verify in provider docs

Do not copy field names or limits from memory. All of the following are **UNVERIFIED**:

- Render free-tier web services: whether they sleep, after how long, and how long a cold start takes.
- Render Docker build limits: time, memory, and image size.
- Current `render.yaml` field names for a Docker web service, including context, Dockerfile path, and environment variables.
- Vercel rewrite behaviour for `/api/*`: whether the browser stays on the Vercel host, whether the `/api` prefix is kept or stripped, and whether the query string is forwarded.
- Whether a rewrite to an external Render URL is allowed on the plan in use.
- Whether Render injects `PORT`, and the exact environment-variable format on both hosts for `ALLOWED_ORIGINS`.
