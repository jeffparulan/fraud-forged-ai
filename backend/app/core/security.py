"""
Security & secrets management.

Fetches secrets from GCP Secret Manager in production,
falls back to env vars for local dev.
"""
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
    """
    Get a secret from GCP Secret Manager or environment variable.

    Args:
        secret_name: Name of the secret in GCP Secret Manager
        fallback_env_var: Environment variable name to use as fallback (local dev)

    Returns:
        Secret value or None if not found
    """
    # Try environment variable first (local dev)
    if fallback_env_var:
        env_value = os.getenv(fallback_env_var)
        if env_value:
            logger.info(f"Using secret from environment variable")
            return env_value

    # Try GCP Secret Manager (production only)
    try:
        project_id = os.getenv('GCP_PROJECT_ID')

        # Skip GCP Secret Manager for local dev
        if project_id == 'local-dev' or not project_id:
            logger.info("Local dev mode - using environment variables only")
            return None

        # Import only if in production
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"

        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode('UTF-8')

        logger.info(f"Retrieved secret from GCP Secret Manager")
        return secret_value

    except ImportError:
        logger.info("GCP Secret Manager not available (local dev mode)")
        return None
    except Exception as e:
        logger.warning(f"Could not retrieve secret from GCP")
        return None


def get_huggingface_token() -> Optional[str]:
    """Get Hugging Face API token"""
    return get_secret('huggingface-api-token', fallback_env_var='HUGGINGFACE_API_TOKEN')
