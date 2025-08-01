#!/bin/bash
# Development startup script

echo "🚀 Starting National League Finance Platform (Development)"

# Load environment variables
if [ -f .env.development ]; then
    export $(cat .env.development | xargs)
fi

# Start services with Docker Compose
docker-compose up --build -d

echo "✅ Services starting..."
echo "📊 API: http://localhost:8000"
echo "📚 Docs: http://localhost:8000/api/v1/docs"
echo "🗄️  PostgreSQL: localhost:5432"
echo "🔴 Redis: localhost:6379"

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
docker-compose ps
