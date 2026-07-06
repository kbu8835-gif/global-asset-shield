# Global Asset Shield Agent V4 Frontend

Hackathon demo frontend for the AI Investment Immune System.

## Positioning

别的 AI 告诉你买什么。我们告诉你什么时候不该买。

This UI demonstrates the full V4 loop:

1. Login / Register
2. User-isolated workspace
3. Immune Scan input
4. AI Risk Scan
5. AI Emotion Scan
6. AI Bias Detector
7. AI Devil's Advocate
8. AI Regret Simulator
9. AI Conviction Score
10. AI Investment Decision
11. Investment Journal
12. AI Review
13. Investment DNA
14. AI Investment Notebook
15. KOL Intelligence V1

## Backend

Start the backend first:

```bash
cd backend
source .venv/bin/activate
uvicorn app:app --reload --port 8010
```

Backend API:

```text
http://127.0.0.1:8010
```

During local frontend development, Vite proxies `/api/*` to `http://127.0.0.1:8010/*`, so the browser demo can call the backend without CORS issues. For deployed builds, set:

```text
VITE_API_BASE_URL=http://localhost:8010
```

If `VITE_API_BASE_URL` is not set, the app falls back to `/api`.

Swagger:

```text
http://127.0.0.1:8010/docs
```

## Install

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Build

```bash
npm run build
```

## Docker

The Docker build serves the frontend with nginx on port `3000`. nginx supports SPA refresh and proxies `/api/*` to the backend service.

See root [DEPLOYMENT.md](../DEPLOYMENT.md).

## Notes

If the backend is not running, the UI shows:

```text
Backend is not running. Please start backend at http://127.0.0.1:8010
```

## Login

The frontend starts on an auth page. Users can login, register, or click Demo Login.

Demo account:

```text
email: demo@globalassetshield.ai
password: demo123456
```

On successful login, the JWT access token is stored in `localStorage` under:

```text
global_asset_shield_token
```

`src/api.ts` automatically sends:

```text
Authorization: Bearer <token>
```

If the backend returns `401`, the token is cleared and the user is returned to the login page. Logout clears the token locally.

## Investment DNA

The bottom section calls:

```text
GET /dna
```

It summarizes the latest journal entries into an investor behavior profile: investor type, discipline, patience, risk appetite, emotion control, independent thinking, conviction, and a direct behavioral summary.

## AI Investment Notebook

The Notebook tab calls:

```text
GET /notebook
GET /notebook/{id}
POST /notebook
PUT /notebook/{id}
POST /notebook/{id}/review
```

It turns Journal entries into editable notes: user writing, AI analysis, AI Coach, user final decision, review, and timeline.

## KOL Intelligence V1

The KOL tab is built around one question:

```text
你正在相信谁？
```

It calls:

```text
GET /kol/profiles
POST /kol/profiles
PUT /kol/profiles/{id}
DELETE /kol/profiles/{id}
GET /kol/profiles/{id}/calls
POST /kol/calls
PUT /kol/calls/{id}
DELETE /kol/calls/{id}
POST /kol/calls/{id}/refresh
POST /kol/profiles/{id}/recalculate
GET /kol/dependency
```

V1 is intentionally manual and free to run: users add KOL profiles and call prices themselves, the system calculates approximate ROI, Trust Score, and KOL Dependency. DNA shows whether the user is outsourcing judgment to KOLs, and Immune Report shows KOL risk warnings when the scan is KOL-driven.
