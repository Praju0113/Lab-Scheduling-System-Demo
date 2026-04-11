# Docker Setup Guide

## Prerequisites
- Docker Desktop installed on your Windows machine
- Docker daemon running

## Quick Start

### Option 1: Using the batch script (Easiest)
1. Double-click `start-docker.bat` - this will start Docker Desktop and build/run containers

### Option 2: Manual steps
1. **Start Docker Desktop**
   - Search for "Docker Desktop" in Windows Start menu
   - Click to launch it
   - Wait for the Docker icon to be ready in system tray (~30-60 seconds)

2. **Open PowerShell/Command Prompt** and navigate to your project root:
   ```bash
   cd "d:\hosting version 2"
   ```

3. **Build and start all containers:**
   ```bash
   docker-compose up --build
   ```

## Accessing the Application

Once all containers are running:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432 (PostgreSQL)

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
- Backend uses port 8000
- Frontend uses port 5173
- PostgreSQL uses port 5432

If these ports are in use, either:
1. Stop the services using those ports
2. Modify the ports in `docker-compose.yml`

### Database connection issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Wait for the health check to pass (shows "healthy" status)

## Project Structure in Docker

```
- postgres (PostgreSQL database)
- backend (FastAPI - http://localhost:8000)
- frontend (Vite + React - http://localhost:5173)
```

All services are on the `lab_network` bridge for internal communication.

## Environment Variables

The `.env` file contains configuration for all services:
- Database credentials
- CORS origins
- API endpoints
- Seed data settings

Edit `.env` to customize configuration.

## Persistence

- Database data is stored in Docker volume `postgres_data`
- To keep data between container restarts: use `docker-compose down` (without `-v`)
- To reset database: use `docker-compose down -v` (removes volume)
