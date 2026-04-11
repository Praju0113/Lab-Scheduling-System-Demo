FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port the backend runs on
EXPOSE 8000

# Run the ASGI wrapper so FastAPI routes and Socket.IO share the same app
CMD ["sh", "-c", "uvicorn app.main:application --host 0.0.0.0 --port 8000 --reload --workers 1"]
