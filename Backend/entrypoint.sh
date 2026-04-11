#!/bin/sh
# Wait for database to be ready, then start the application

echo "Waiting for PostgreSQL at postgres:5432..."

counter=0
max_attempts=30

while [ $counter -lt $max_attempts ]; do
    if (timeout 1 bash -c "</dev/tcp/postgres/5432") 2>/dev/null; then
        echo "PostgreSQL is ready!"
        break
    fi
    counter=$((counter + 1))
    echo "Attempt $counter/$max_attempts: PostgreSQL not ready yet. Waiting..."
    sleep 2
done

if [ $counter -ge $max_attempts ]; then
    echo "Error: PostgreSQL did not become ready in time"
    exit 1
fi

# Start the mounted ASGI application so /socket.io is available
exec uvicorn app.main:application --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" --reload
