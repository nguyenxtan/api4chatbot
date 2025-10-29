#!/bin/bash

# Deploy script for Ubuntu server

echo "🚀 Deploying API4Chatbot..."

# Stop and remove existing containers
echo "📦 Stopping existing containers..."
docker-compose down

# Remove old images (optional - uncomment if needed)
# docker-compose down --rmi all

# Pull latest changes (if using git)
# git pull origin main

# Build and start containers
echo "🔨 Building Docker image..."
docker-compose build --no-cache

echo "▶️  Starting containers..."
docker-compose up -d

# Show logs
echo "📋 Container logs:"
docker-compose logs --tail=50

# Show status
echo ""
echo "✅ Deployment complete!"
echo ""
docker-compose ps

echo ""
echo "📊 To view logs: docker-compose logs -f"
echo "🛑 To stop: docker-compose down"
echo "🔄 To restart: docker-compose restart"
