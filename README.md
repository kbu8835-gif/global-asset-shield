# Global Asset Shield V1.0 Beta

AI Investment Immune System / AI 投资免疫系统

别的 AI 告诉你买什么。Global Asset Shield 告诉你什么时候不该买。

## Apps

- `backend/`: FastAPI API, auth, scanners, notebook, DNA, KOL Intelligence
- `frontend/`: Vite React demo app
- `docker-compose.yml`: PostgreSQL + backend + frontend stack

## Local Development

```bash
cd backend
source .venv/bin/activate
uvicorn app:app --reload --port 8010
```

```bash
cd frontend
npm run dev
```

## Docker

```bash
cp backend/.env.docker.example backend/.env.docker
cp frontend/.env.docker.example frontend/.env.docker
docker compose up -d --build
```

Open:

- Frontend: http://localhost:3000
- Backend: http://localhost:8010
- API Docs: http://localhost:8010/docs
- Health: http://localhost:8010/health

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md).

Before production, change `JWT_SECRET`, `POSTGRES_PASSWORD`, and `DEMO_USER_PASSWORD`.
