# Global Asset Shield Deployment

V1.0 Beta deployment guide for Global Asset Shield Agent / AI Investment Immune System.

## Local Development

Backend defaults to SQLite when `DATABASE_URL` is not set.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8010
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8010
Docs:     http://127.0.0.1:8010/docs
Health:   http://127.0.0.1:8010/health
```

## Docker

Create real env files from the examples before production deployment:

```bash
cp backend/.env.docker.example backend/.env.docker
cp frontend/.env.docker.example frontend/.env.docker
```

Start the stack:

```bash
docker compose up --build
```

Or run in the background:

```bash
docker compose up -d --build
```

Open:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8010
Docs:     http://localhost:8010/docs
Health:   http://localhost:8010/health
```

## Services

`db`

- Image: `postgres:16`
- Database: `global_asset_shield`
- User: `gas_user`
- Port: `5432`
- Data volume: `postgres_data`

`backend`

- Builds from `backend/Dockerfile`
- Runs FastAPI on port `8010`
- Reads `backend/.env.docker`
- Uses PostgreSQL through `DATABASE_URL`

`frontend`

- Builds from `frontend/Dockerfile`
- Builds Vite React assets
- Serves through nginx on port `3000`
- Proxies `/api/*` to `backend:8010`

## Environment Variables

Backend:

```text
APP_ENV=development
DATABASE_URL=sqlite:///./data/investment_journal.db
JWT_SECRET=change_me_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DEMO_USER_EMAIL=demo@globalassetshield.ai
DEMO_USER_PASSWORD=demo123456
```

Docker PostgreSQL:

```text
DATABASE_URL=postgresql://gas_user:gas_password@db:5432/global_asset_shield
```

Frontend:

```text
VITE_API_BASE_URL=http://localhost:8010
```

If `VITE_API_BASE_URL` is not set, the frontend falls back to `/api`, which works in Docker because nginx proxies `/api` to the backend service.

## PostgreSQL Notes

The backend now supports two database modes:

- SQLite: local development default
- PostgreSQL: Docker / production default

Tables are created automatically on startup:

- `users`
- `journal_entries`
- `kol_profiles`
- `kol_calls`

Existing SQLite data remains compatible. In PostgreSQL, the same user isolation rules apply to Journal, Notebook, DNA, KOL Profiles, KOL Calls, and Immune Reports.

## Production Checklist

Before going live, change:

- `JWT_SECRET`
- `POSTGRES_PASSWORD`
- `DEMO_USER_PASSWORD`

Do not commit real `.env` or `.env.docker` files. Keep only:

- `.env.example`
- `.env.docker.example`

Recommended next production steps:

- Put the frontend and backend behind HTTPS
- Use a managed PostgreSQL instance or a backed-up Docker volume
- Rotate demo credentials or disable demo login
- Set `CORS_ORIGINS` to your real domain

## Common Issues

Backend cannot connect to database:

- Check `DATABASE_URL`
- Check that Postgres is healthy: `docker compose ps`
- Check backend logs: `docker compose logs backend`

Frontend loads but API calls fail:

- Check backend health: `curl http://localhost:8010/health`
- If using direct API mode, check `VITE_API_BASE_URL`
- If using nginx proxy mode, check `/api` routing in `frontend/nginx.conf`

Demo login fails:

- Check that backend started successfully
- Check `DEMO_USER_EMAIL` and `DEMO_USER_PASSWORD`
- Check `/auth/login` with curl
