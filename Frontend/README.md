# Frontend

React + Vite frontend for the lab scheduling system.

## Stack
- React
- Vite
- Tailwind CSS
- Axios
- Socket.IO client
- Zustand

## Requirements
- Node.js 20+
- npm

## Environment
The frontend reads Vite environment variables from the repository root `.env`.

Example:

```env
FRONTEND_PORT=5173
VITE_API_BASE_URL=http://localhost:8000
```

The app also supports `VITE_API_URL`, but one of those variables must exist in the repository root `.env`.

## Install
```cmd
cd /d D:\LSS-DEMO\Frontend
npm install
```

## Run Locally
```cmd
cd /d D:\LSS-DEMO\Frontend
npm run dev
```

Default dev URL when `FRONTEND_PORT=5173`:

```text
http://localhost:5173
```

## Build
```cmd
cd /d D:\LSS-DEMO\Frontend
npm run build
```

## Docker
From the repository root:

```cmd
cd /d D:\LSS-DEMO
docker compose up --build frontend
```

## Notes
- API requests are routed through the configured Vite proxy in development.
- Realtime updates use Socket.IO and expect the backend to serve the mounted ASGI application at `/socket.io`.
