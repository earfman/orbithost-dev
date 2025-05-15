# OrbitHost - AI-Native Hosting Platform

OrbitHost is an open-source platform that automatically deploys web projects from GitHub and sends structured deployment data back to AI agents for further action.

## 🎯 Project Overview

OrbitHost provides a seamless connection between your code and AI agents by:

- Automatically deploying web projects from GitHub
- Detecting when a deployed site is live and accessible
- Capturing screenshots and the DOM (HTML) of the deployed site
- Sending structured webhooks with that data to your AI agent

## 🛠️ Core Features

- **GitHub Webhook Listener**: Detect push events and capture metadata
- **Deploy Engine**: Deploy web applications to Fly.io
- **Screenshot Capture**: Take screenshots of deployed sites
- **DOM Extraction**: Capture the HTML structure for AI analysis
- **Webhook Delivery**: Send structured data to AI agents

## 📚 Tech Stack

- **Backend**: FastAPI (Python)
- **Deployment**: Fly.io
- **Screenshots**: Playwright
- **Infrastructure**: Docker + GitHub Actions

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Docker
- Fly.io account
- GitHub repository

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/orbit-host.git
cd orbit-host

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Copy the example environment file and update with your credentials:
```bash
cp .env.example .env
```

### Running Locally
```bash
# Start the backend
cd backend
uvicorn main:app --reload
```

## 📁 Project Structure

```
orbit-host/
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Core functionality
│   │   ├── models/          # Data models
│   │   ├── services/        # Business logic
│   │   └── utils/           # Utility functions
│   ├── tests/               # Backend tests
│   └── requirements.txt     # Python dependencies
├── docs/                    # Documentation
├── Dockerfile               # Container definition
├── fly.toml                 # Fly.io configuration
└── README.md                # Project overview
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the [OrbitHost Source Available License](LICENSE) (OSAL).

The OSAL allows:
- Personal and non-commercial use without restriction
- Internal business use
- Commercial use only through the official OrbitHost service

The license prohibits creating competing products with similar functionality.
