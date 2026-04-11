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
Copy `.env.example` to `.env` and set your PostgreSQL connection string.

Required:
- `DATABASE_URL`

Optional:
- `SEED_ON_STARTUP=true`
- `RESET_DB_ON_STARTUP=true`
- `BACKEND_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`

Notes:
- Local development also accepts common LAN/dev origins such as `localhost`, `127.0.0.1`, `0.0.0.0`, and private network IPs on arbitrary ports.
- Set `BACKEND_CORS_ORIGINS=*` if you explicitly want to allow every origin.

## Install
```cmd
cd /d "D:\LAB_Sheduling\scalable backend"
C:\Users\praju\miniconda3\Scripts\activate.bat
conda activate labqs
pip install -r requirements.txt
```

## Run
```cmd
cd /d "D:\LAB_Sheduling\scalable backend"
C:\Users\praju\miniconda3\Scripts\activate.bat
conda activate labqs
python -m uvicorn app.main:application --host 127.0.0.1 --port 8021 --reload
```
