# Scalable Backend

Parallel PostgreSQL-backed backend for the lab scheduling system.

## Features
- PostgreSQL persistence for visits, tests, labs, specialists, queues, and assignment history
- Incremental scheduling operations instead of global JSON-state refreshes
- Socket.io events for targeted frontend updates
- Frontend-compatible bootstrap and queue APIs
- Paginated visit listing and delta update APIs
- Separate dev seed flow

## Environment
Use the repository root `.env` as the source of truth for backend and frontend runtime configuration.

Required:
- `DATABASE_URL`
- `BACKEND_CORS_ORIGINS`

Optional:
- `POSTGRES_PORT=5432`
- `BACKEND_PORT=8000`
- `FRONTEND_PORT=5173`
- `SEED_ON_STARTUP=true`
- `RESET_DB_ON_STARTUP=true`
- `VITE_API_BASE_URL=http://localhost:8000`

## Install
```cmd
cd /d "D:\LSS-DEMO\Backend"
C:\Users\praju\miniconda3\Scripts\activate.bat
conda activate labqs
pip install -r requirements.txt
```

## Run
```cmd
cd /d "D:\LSS-DEMO\Backend"
C:\Users\praju\miniconda3\Scripts\activate.bat
conda activate labqs
python -m uvicorn app.main:application --host 0.0.0.0 --port 8000 --reload
```
