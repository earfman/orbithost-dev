# OrbitHost Secrets Management Guide

## Overview

This guide explains the secrets management system implemented in OrbitHost to securely handle API keys, database credentials, and other sensitive information.

## Features

- **Layered Access**: Secrets are retrieved from multiple sources in order of priority
- **Encryption**: Optional encryption for secrets stored in files
- **Environment Validation**: Validation of required secrets based on environment
- **Centralized Configuration**: All settings managed through a single configuration system

## How It Works

### 1. Sources of Secrets (in order of priority)

1. **Environment Variables**: Highest priority, set at runtime
2. **Secrets File**: JSON file that can be encrypted, loaded at startup
3. **Settings Defaults**: Fallback values defined in the settings class

### 2. Using the Secrets Manager

```python
from app.utils.secrets import get_secret, set_secret, delete_secret

# Get a secret (checks environment variables first, then secrets file)
api_key = get_secret("API_KEY")

# Set a secret (saves to secrets file)
set_secret("NEW_API_KEY", "your-api-key-value")

# Delete a secret
delete_secret("OLD_API_KEY")
```

### 3. Configuration Settings

The application uses Pydantic's `BaseSettings` for configuration, which automatically loads values from environment variables:

```python
from app.core.config import settings

# Access settings
supabase_url = settings.SUPABASE_URL
debug_mode = settings.DEBUG
```

## Security Best Practices

1. **Never commit secrets to Git**:
   - Use `.env` files for local development (added to `.gitignore`)
   - Use environment variables in production environments
   - Use encrypted secrets files for shared environments

2. **Rotate secrets regularly**:
   - Implement a process for regular rotation of API keys and credentials
   - Update all instances when rotating secrets

3. **Limit access to secrets**:
   - Only services that need a specific secret should have access to it
   - Use different secrets for different environments (dev, staging, prod)

## Setting Up for Development

1. Create a `.env` file in the project root with your secrets:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-key
   CLERK_API_KEY=your-clerk-api-key
   ```

2. Alternatively, create an encrypted secrets file:
   ```bash
   # Set encryption key in environment
   export ENCRYPTION_KEY="your-secure-encryption-key"
   
   # Create secrets directory
   mkdir -p secrets
   
   # Create a secrets.json file with your secrets
   echo '{
     "SUPABASE_URL": "https://your-project.supabase.co",
     "SUPABASE_KEY": "your-supabase-key"
   }' > secrets/secrets.json
   
   # Point to the secrets file
   export SECRETS_FILE="secrets/secrets.json"
   ```

## Setting Up for Production

For production environments, set secrets as environment variables in your deployment platform:

### Fly.io

```bash
fly secrets set SUPABASE_URL=https://your-project.supabase.co
fly secrets set SUPABASE_KEY=your-supabase-key
fly secrets set CLERK_API_KEY=your-clerk-api-key
```

### Docker

```bash
docker run -e SUPABASE_URL=https://your-project.supabase.co \
           -e SUPABASE_KEY=your-supabase-key \
           -e CLERK_API_KEY=your-clerk-api-key \
           orbithost/api
```

## Troubleshooting

If you encounter issues with secrets:

1. Check that all required environment variables are set
2. Verify that the secrets file exists and is readable
3. Ensure the encryption key is correct if using encrypted secrets
4. Check application logs for specific error messages

## Further Enhancements

Future improvements to the secrets management system may include:

- Integration with cloud secret management services (AWS Secrets Manager, GCP Secret Manager)
- Automatic secret rotation
- Secret access auditing
- Multi-environment secret configuration
