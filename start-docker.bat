@echo off
REM Start Docker Desktop
echo.
echo ===================================
echo Starting Docker Desktop...
echo ===================================
echo.

REM Try to start Docker Desktop
"C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo.
echo Waiting for Docker to be ready...
timeout /t 10

REM Navigate to project and run docker-compose
cd /d "d:\hosting version 2"
echo.
echo ===================================
echo Building and starting containers...
echo ===================================
echo.
docker-compose up --build

pause
