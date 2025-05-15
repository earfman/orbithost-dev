# OrbitHost Self-Deployment Guide

This document outlines how OrbitHost uses itself for deployment - a practice known as "dogfooding" - using a hybrid approach with public and private components.

## What is Dogfooding?

Dogfooding refers to the practice of using your own product in real-world conditions. For OrbitHost, this means:

1. Using OrbitHost to deploy itself
2. Capturing screenshots of its own deployments
3. Sending webhooks to our own AI agents
4. Using the feedback to improve the platform

## Self-Deployment Architecture

OrbitHost uses a hybrid approach with public open-source components and private proprietary features:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Public GitHub  │────▶│  Your OrbitHost │────▶│  Deployed       │
│  Repository     │     │  Instance       │     │  OrbitHost      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Screenshot     │────▶│  AI Agent       │
                        │  Capture        │     │  Webhook        │
                        └─────────────────┘     └─────────────────┘
```

### Public vs. Private Components

**Public Components** (in GitHub repository):
- Core webhook listener and deployment engine
- Screenshot and DOM capture functionality
- Basic documentation and examples
- Deployment configuration templates

**Private Components** (not in public repository):
- Specific implementation of paid features
- Actual billing integration code
- Production infrastructure configuration
- Proprietary AI integration details

## How It Works

1. **Initial Setup**: The first deployment is done manually using `flyctl deploy`
2. **GitHub Integration**: We connect our public GitHub repository to our hosted OrbitHost instance
3. **Webhook Configuration**: Our OrbitHost instance listens for pushes to the public repository
4. **Deployment Process**:
   - When code is pushed to the public repository, our OrbitHost instance receives the webhook
   - OrbitHost deploys the updated version to Fly.io
   - OrbitHost captures a screenshot of its own deployment
   - OrbitHost sends the deployment data to its own AI agent
5. **Monitoring**: We use our own metrics, logging, and tracing systems to monitor the deployment
   - Phase 1: Basic Prometheus metrics
   - Phase 2: Structured logging with Zap
   - Phase 3: Simplified tracing implementation
   - Phase 4: Dashboards and alerts

## Benefits of Self-Deployment

1. **Real-World Testing**: We experience OrbitHost exactly as our users do
2. **Immediate Feedback**: Issues are discovered quickly during our own development
3. **Confidence Building**: If OrbitHost can deploy itself reliably, it can deploy other projects
4. **Showcase**: Demonstrates the platform's capabilities with a real example

## Implementation Details

The self-deployment process uses:

- `fly.toml`: Configuration for Fly.io deployment
- `Dockerfile`: Multi-stage build for optimized container
- `scripts/self-deploy.sh`: Script to automate the self-deployment process
- GitHub webhook pointing to our own OrbitHost instance

## Getting Started with Self-Deployment

1. Prepare your repository structure:
   - Ensure sensitive information is removed from public components
   - Create proper .gitignore and .env.example files
   - Document the open-source core functionality

2. Push the public components to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial OrbitHost commit"
   git remote add origin https://github.com/yourusername/orbit-host.git
   git push -u origin main
   ```

3. Deploy your complete instance (including private components):
   ```bash
   ./scripts/self-deploy.sh
   ```

4. Configure the GitHub webhook to point to your deployed instance:
   - Go to your GitHub repository settings
   - Add a webhook pointing to your OrbitHost instance
   - Set the secret token in your environment variables

5. Make a change to the public repository, push it, and watch your OrbitHost instance deploy itself!

## Monitoring Self-Deployments

We've created a special dashboard for monitoring OrbitHost's own deployments:

- Deployment status and history
- Performance metrics
- Screenshot gallery of past deployments
- Webhook delivery logs

This dashboard is available at: `https://orbithost.app/admin/self-deployments`
