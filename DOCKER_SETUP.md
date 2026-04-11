# Docker Setup Guide

## Prerequisites
- Docker Desktop installed on your Windows machine
- Docker daemon running

## Quick Start

### Option 1: Using the batch script (Easiest)
1. Open a terminal in the repository root and run `docker compose up --build`

### Option 2: Manual steps
1. **Start Docker Desktop**
   - Search for "Docker Desktop" in Windows Start menu
   - Click to launch it
   - Wait for the Docker icon to be ready in system tray (~30-60 seconds)

2. **Open PowerShell/Command Prompt** and navigate to your project root:
   ```bash
   cd "D:\LSS-DEMO"
   ```

3. **Build and start all containers:**
   ```bash
   docker-compose up --build
   ```

## Accessing the Application

Once all containers are running:

- **Frontend**: `http://<host>:${FRONTEND_PORT}`
- **Backend API**: `http://<host>:${BACKEND_PORT}`
- **API Docs**: `http://<host>:${BACKEND_PORT}/docs`
- **Database**: `<host>:${POSTGRES_PORT}` (PostgreSQL)

## Common Commands

### Start containers (without rebuild)
```bash
docker-compose up
```

### Stop containers
```bash
docker-compose down
```

### Stop and remove all data
```bash
docker-compose down -v
```

### View logs
```bash
docker-compose logs -f
```

### View logs for specific service
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Rebuild a specific service
```bash
docker-compose up --build backend
```

## Troubleshooting

### Docker daemon not running
- Start Docker Desktop from Windows Start menu
- Wait for the Docker icon in system tray to show it's ready

### Port already in use
- Backend uses `BACKEND_PORT`
- Frontend uses `FRONTEND_PORT`
- PostgreSQL uses `POSTGRES_PORT`

If these ports are in use, either:
1. Stop the services using those ports
2. Modify the port variables in the root `.env`

### Database connection issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Wait for the health check to pass (shows "healthy" status)

## Project Structure in Docker

```
- postgres (PostgreSQL database)
- backend (FastAPI - `http://<host>:${BACKEND_PORT}`)
- frontend (Vite + React - `http://<host>:${FRONTEND_PORT}`)
```

All services are on the `lab_network` bridge for internal communication.

## Environment Variables

The `.env` file contains configuration for all services:
- Database credentials
- Published ports
- CORS origins
- API endpoints
- Seed data settings

Edit `.env` to customize configuration.

## Persistence

- Database data is stored in Docker volume `postgres_data`
- To keep data between container restarts: use `docker-compose down` (without `-v`)
- To reset database: use `docker-compose down -v` (removes volume)
