"""HashiCorp Vault client wrapper for secret management."""

import logging
import os
from functools import lru_cache
from typing import Any, Optional

import hvac
from dotenv import load_dotenv

# Load .env into the process environment BEFORE any os.getenv() fallback reads
# run. The secret manager and Settings.__init__ run before pydantic-settings'
# own env_file handling, so without this the .env values are invisible.
#
# override=True: the .env file is the source of truth for local dev. Without
# this, a stale DATABASE_URL left in a shell session (e.g. sqlite:///...) would
# silently shadow the Postgres URL in .env, because python-dotenv does not
# overwrite already-set environment variables by default.
load_dotenv(override=True)

logger = logging.getLogger(__name__)


class VaultClient:
    """Wrapper around hvac client for fetching secrets from Vault."""

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        namespace: Optional[str] = None,
        mount_point: str = "secret",
    ):
        self.url = url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.getenv("VAULT_TOKEN")
        self.namespace = namespace or os.getenv("VAULT_NAMESPACE")
        self.mount_point = mount_point
        self._client: Optional[hvac.Client] = None
        self._initialized = False

    def _get_client(self) -> hvac.Client:
        """Get or create hvac client."""
        if self._client is None:
            self._client = hvac.Client(
                url=self.url,
                token=self.token,
                namespace=self.namespace,
            )
        return self._client

    def is_available(self) -> bool:
        """Check if Vault is reachable and authenticated."""
        try:
            client = self._get_client()
            return client.is_authenticated()
        except Exception as e:
            logger.debug("Vault not available: %s", e)
            return False

    def read_secret(self, path: str, key: Optional[str] = None) -> Optional[Any]:
        """
        Read a secret from Vault KV v2.

        Args:
            path: Secret path (e.g., "scout-io/prod/database_url")
            key: Specific key within the secret (optional, returns all if None)

        Returns:
            Secret value or dict of all keys, or None if not found
        """
        try:
            client = self._get_client()
            full_path = f"{self.mount_point}/data/{path}"
            response = client.secrets.kv.v2.read_secret_version(path=path, mount_point=self.mount_point)

            data = response["data"]["data"]
            if key:
                return data.get(key)
            return data
        except hvac.exceptions.InvalidPath:
            logger.debug("Secret not found at path: %s", path)
            return None
        except Exception as e:
            logger.warning("Failed to read secret from Vault at %s: %s", path, e)
            return None

    def write_secret(self, path: str, secret: dict) -> bool:
        """
        Write a secret to Vault KV v2.

        Args:
            path: Secret path
            secret: Dictionary of key-value pairs to store

        Returns:
            True if successful
        """
        try:
            client = self._get_client()
            client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret,
                mount_point=self.mount_point,
            )
            return True
        except Exception as e:
            logger.error("Failed to write secret to Vault at %s: %s", path, e)
            return False

    def delete_secret(self, path: str) -> bool:
        """Delete a secret from Vault."""
        try:
            client = self._get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=self.mount_point,
            )
            return True
        except Exception as e:
            logger.error("Failed to delete secret from Vault at %s: %s", path, e)
            return False


class SecretManager:
    """
    High-level secret manager that fetches from Vault with env var fallback.

    In production, Vault is required. In development, falls back to environment
    variables if Vault is unavailable.
    """

    # Secret path convention: secret/scout-io/<env>/<key>
    # Env-specific paths are resolved at runtime based on DEPLOYMENT_ENV

    def __init__(
        self,
        vault_client: Optional[VaultClient] = None,
        env: Optional[str] = None,
        require_vault: bool = False,
    ):
        self.vault = vault_client or VaultClient()
        self.env = env or os.getenv("DEPLOYMENT_ENV", "development")
        self.require_vault = require_vault or self.env == "production"
        self._cache: dict[str, Any] = {}
        self._vault_available: Optional[bool] = None

    def _check_vault(self) -> bool:
        """Check Vault availability (cached)."""
        if self._vault_available is None:
            self._vault_available = self.vault.is_available()
            if self._vault_available:
                logger.info("Vault is available at %s", self.vault.url)
            else:
                if self.require_vault:
                    logger.error("Vault is required but not available at %s", self.vault.url)
                else:
                    logger.warning("Vault not available, falling back to environment variables")
        return self._vault_available

    def _vault_path(self, key: str) -> str:
        """Build Vault path for a secret key."""
        return f"scout-io/{self.env}/{key}"

    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Get a secret value.

        Priority:
        1. Vault (if available and required)
        2. Environment variable
        3. Default value

        Args:
            key: Secret key (e.g., "database_url", "jwt_secret")
            default: Default value if not found anywhere

        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        vault_available = self._check_vault()

        # Try Vault first if available
        if vault_available:
            vault_path = self._vault_path(key)
            value = self.vault.read_secret(vault_path)
            if value is not None:
                self._cache[key] = value
                return value

            # If Vault is required but secret not found, raise error
            if self.require_vault:
                raise RuntimeError(
                    f"Required secret '{key}' not found in Vault at {vault_path}. "
                    f"Ensure secret is provisioned in Vault."
                )

        # Fallback to environment variable
        env_key = key.upper()
        env_value = os.getenv(env_key)
        if env_value is not None:
            self._cache[key] = env_value
            return env_value

        # Return default
        return default

    def get_secret_or_raise(self, key: str) -> Any:
        """
        Get a secret value, raising if not found.

        In production, this will fail if Vault is unavailable or secret missing.
        In development, falls back to env var.
        """
        value = self.get_secret(key)
        if value is None:
            raise RuntimeError(
                f"Secret '{key}' not found. "
                f"Checked Vault (path: {self._vault_path(key)}) and environment variable ({key.upper()})."
            )
        return value

    def get_database_url(self) -> str:
        """Get database URL from Vault or environment."""
        return self.get_secret_or_raise("database_url")

    def get_redis_url(self) -> str:
        """Get Redis URL from Vault or environment."""
        return self.get_secret_or_raise("redis_url")

    def get_jwt_secret(self) -> str:
        """Get JWT secret from Vault or environment."""
        return self.get_secret_or_raise("jwt_secret")

    def get_qdrant_url(self) -> str:
        """Get Qdrant URL from Vault or environment."""
        return self.get_secret_or_raise("qdrant_url")

    def get_qdrant_api_key(self) -> Optional[str]:
        """Get Qdrant API key from Vault or environment."""
        return self.get_secret("qdrant_api_key")

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from Vault or environment."""
        return self.get_secret("openai_api_key")

    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from Vault or environment."""
        return self.get_secret("anthropic_api_key")

    def get_together_api_key(self) -> Optional[str]:
        """Get Together AI API key from Vault or environment."""
        return self.get_secret("together_api_key")

    def get_gemini_api_key(self) -> Optional[str]:
        """Get Google Gemini API key from Vault or environment."""
        return self.get_secret("gemini_api_key")

    def get_azure_openai_api_key(self) -> Optional[str]:
        """Get Azure OpenAI API key from Vault or environment."""
        return self.get_secret("azure_openai_api_key")

    def get_celery_broker_url(self) -> str:
        """Get Celery broker URL from Vault or environment."""
        return self.get_secret_or_raise("celery_broker_url")

    def get_celery_result_backend(self) -> str:
        """Get Celery result backend from Vault or environment."""
        return self.get_secret_or_raise("celery_result_backend")

    def get_webhook_secret(self) -> Optional[str]:
        """Get webhook signing secret from Vault or environment."""
        return self.get_secret("webhook_secret")

    def get_razorpay_key_id(self) -> Optional[str]:
        """Get Razorpay Key ID from Vault or environment."""
        return self.get_secret("razorpay_key_id")

    def get_razorpay_key_secret(self) -> Optional[str]:
        """Get Razorpay Key Secret from Vault or environment."""
        return self.get_secret("razorpay_key_secret")

    def get_razorpay_webhook_secret(self) -> Optional[str]:
        """Get Razorpay webhook signing secret from Vault or environment."""
        return self.get_secret("razorpay_webhook_secret")


# Global instance
_secret_manager: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """Get the global SecretManager instance."""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManager()
    return _secret_manager


def init_secret_manager(
    vault_url: Optional[str] = None,
    vault_token: Optional[str] = None,
    env: Optional[str] = None,
    require_vault: bool = False,
) -> SecretManager:
    """Initialize the global SecretManager with custom settings."""
    global _secret_manager
    vault_client = VaultClient(url=vault_url, token=vault_token)
    _secret_manager = SecretManager(
        vault_client=vault_client,
        env=env,
        require_vault=require_vault,
    )
    return _secret_manager