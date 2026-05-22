# app/core/config.py
# This module loads all environment variables from the .env file
# and makes them available throughout the app as typed Python objects.

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Pydantic automatically reads from the .env file.
    """

    # --- App Info ---
    app_name: str = Field(default="AI Code Reviewer", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # --- Server ---
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # --- OpenAI ---
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.1, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=4000, alias="OPENAI_MAX_TOKENS")

    # --- GitHub ---
    github_token: str = Field(default="", alias="GITHUB_TOKEN")

    # --- ChromaDB ---
    chroma_persist_directory: str = Field(
        default="./chroma_db", alias="CHROMA_PERSIST_DIRECTORY"
    )
    chroma_collection_name: str = Field(
        default="code_reviews", alias="CHROMA_COLLECTION_NAME"
    )

    class Config:
        # Tell pydantic where to find the .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow both alias and field name
        populate_by_name = True


# Create a single shared instance used across the entire app
settings = Settings()