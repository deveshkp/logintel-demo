#!/bin/bash

# Docker Hub Push Script for LogIntel Demo
# Usage: ./push-to-dockerhub.sh [dockerhub-username]

DOCKERHUB_USER=${1:-deveshpandey}

echo "🚀 Pushing LogIntel images to Docker Hub..."
echo "Using Docker Hub username: $DOCKERHUB_USER"

# Tag images
echo "📝 Tagging images..."
docker tag logintel-mcp-server:latest $DOCKERHUB_USER/logintel-mcp-server:latest
docker tag logintel-ui:latest $DOCKERHUB_USER/logintel-ui:latest

# Push images
echo "⬆️  Pushing MCP Server image..."
docker push $DOCKERHUB_USER/logintel-mcp-server:latest

echo "⬆️  Pushing UI image..."
docker push $DOCKERHUB_USER/logintel-ui:latest

echo "✅ All images pushed successfully!"
echo ""
echo "📋 Images available at:"
echo "  - https://hub.docker.com/r/$DOCKERHUB_USER/logintel-mcp-server"
echo "  - https://hub.docker.com/r/$DOCKERHUB_USER/logintel-ui"
echo ""
echo "🔧 To use these images in docker-compose.yml, update the image references:"
echo "  mcp-server:"
echo "    image: $DOCKERHUB_USER/logintel-mcp-server:latest"
echo "  ui:"
echo "    image: $DOCKERHUB_USER/logintel-ui:latest"