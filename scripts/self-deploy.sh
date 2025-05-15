#!/bin/bash
# Self-deployment script for OrbitHost
# This script is used by OrbitHost to deploy itself to Fly.io

set -e

echo "🚀 Starting OrbitHost self-deployment..."

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check if we have the necessary tools
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl not found. Please install Fly.io CLI first."
    echo "   Run: curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if we're logged in to Fly.io
if ! flyctl auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io. Please run 'flyctl auth login' first."
    exit 1
fi

# Build and deploy
echo "🏗️ Building OrbitHost..."
flyctl deploy --remote-only

# Check deployment status
echo "🔍 Checking deployment status..."
if flyctl status; then
    echo "✅ OrbitHost successfully deployed itself!"
    
    # Get the deployment URL
    APP_NAME=$(grep "app =" fly.toml | cut -d'"' -f2 || echo "orbithost")
    DEPLOY_URL="https://${APP_NAME}.fly.dev"
    
    echo "🌐 Deployment URL: $DEPLOY_URL"
    
    # Take a screenshot of our own deployment (dogfooding!)
    echo "📸 Capturing screenshot of our own deployment..."
    
    # In a real implementation, we would use our own API to capture this
    # For now, we'll just print a message
    echo "   This is where OrbitHost would use its own screenshot service"
    echo "   to capture a screenshot of $DEPLOY_URL"
    
    # Send webhook to our own AI agent (more dogfooding!)
    echo "🤖 Sending webhook to our own AI agent..."
    echo "   This is where OrbitHost would send deployment data to its own AI agent"
    
    echo "🎉 Self-deployment complete! OrbitHost is now hosting itself."
else
    echo "❌ Deployment check failed. Please check the logs for more information."
    exit 1
fi
