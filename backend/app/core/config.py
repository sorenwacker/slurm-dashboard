from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = "production"  # production, development, or staging

    # API Settings
    api_title: str = "Slurm Usage History API"
    api_version: str = "1.0.0"
    api_prefix: str = "/api"

    # Security (comma-separated string)
    api_keys: str = ""
    secret_key: str = "change-this-to-a-random-secret-key-in-production"

    # Admin (comma-separated: username:hashed_password)
    admin_users: str = ""
    admin_secret_key: str = "change-this-to-a-random-secret-key-in-production"

    # SAML-based admin emails (comma-separated: email:role)
    # Example: admin@example.com:superadmin,user@example.com:admin
    admin_emails: str = ""
    superadmin_emails: str = ""  # Comma-separated list of superadmin emails

    # Data
    data_path: str = "data"
    cluster_config_path: str | None = None  # writable clusters.yaml; default is inside the checkout
    auto_refresh_interval: int = 600

    # CORS (comma-separated string)
    cors_origins: str = "http://localhost:3100"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    def get_api_keys(self) -> list[str]:
        """Parse API keys from comma-separated string."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.cors_origins:
            return []
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def get_admin_users(self) -> dict[str, str]:
        """Parse admin users from comma-separated string.

        Format: username:hashed_password,username2:hashed_password2
        Returns: {"username": "hashed_password", ...}
        """
        if not self.admin_users:
            return {}

        users = {}
        for raw_user_entry in self.admin_users.split(","):
            user_entry = raw_user_entry.strip()
            if ":" in user_entry:
                username, password_hash = user_entry.split(":", 1)
                users[username.strip()] = password_hash.strip()

        return users

    def get_admin_email_roles(self) -> dict[str, str]:
        """Parse admin emails with roles from configuration.

        Reads from database first, falls back to environment variables.
        Returns: {"email@example.com": "admin"|"superadmin", ...}
        """
        import json
        from pathlib import Path

        from ..models.admin_models import AdminRole

        email_roles = {}

        # Try reading from database first
        db_path = Path("data/clusters.json")
        db_admin_emails = []
        db_superadmin_emails = []

        if db_path.exists():
            try:
                with open(db_path) as f:
                    data = json.load(f)
                if "admin_users" in data:
                    db_admin_emails = data["admin_users"].get("admin_emails", [])
                    db_superadmin_emails = data["admin_users"].get("superadmin_emails", [])
            except Exception:
                pass  # Fall back to environment variables

        # Add superadmin emails from database
        for email in db_superadmin_emails:
            if email:
                email_roles[email.lower()] = AdminRole.SUPERADMIN

        # Add admin emails from database
        for email in db_admin_emails:
            if email:
                email_roles[email.lower()] = AdminRole.ADMIN

        # Fall back to environment variables if database doesn't have them
        if not email_roles:
            # First, add all superadmin emails from env
            if self.superadmin_emails:
                for raw_email in self.superadmin_emails.split(","):
                    email = raw_email.strip()
                    if email:
                        email_roles[email.lower()] = AdminRole.SUPERADMIN

            # Then add emails from admin_emails (format: email:role)
            if self.admin_emails:
                for raw_entry in self.admin_emails.split(","):
                    entry = raw_entry.strip()
                    if ":" in entry:
                        email, role = entry.split(":", 1)
                        email = email.strip().lower()
                        role = role.strip().lower()
                        if role in ["admin", "superadmin"]:
                            email_roles[email] = AdminRole.SUPERADMIN if role == "superadmin" else AdminRole.ADMIN
                    elif entry:
                        # If no role specified, default to admin
                        email_roles[entry.lower()] = AdminRole.ADMIN

        return email_roles

    def is_admin_email(self, email: str) -> bool:
        """Check if an email is in the admin list."""
        if not email:
            return False
        email_roles = self.get_admin_email_roles()
        return email.lower() in email_roles

    def get_email_role(self, email: str) -> str | None:
        """Get the role for a given email address."""
        if not email:
            return None
        email_roles = self.get_admin_email_roles()
        return email_roles.get(email.lower())

    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ["development", "dev"]

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ["production", "prod"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data path is absolute
        if not Path(self.data_path).is_absolute():
            self.data_path = str(Path.cwd() / self.data_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
