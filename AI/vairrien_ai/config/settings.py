from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """
    Central configuration for Vairrien AI.

    Environment variables control model providers,
    model selection, API configuration, and runtime behavior.
    """

    # ========================================================
    # APPLICATION
    # ========================================================

    app_name: str = "Vairrien AI"

    environment: str = os.getenv(
        "VAIRRIEN_ENV",
        "development",
    )

    # ========================================================
    # TEXT MODEL
    # ========================================================

    model_provider: str = os.getenv(
        "VAIRRIEN_MODEL_PROVIDER",
        "openrouter",
    )

    model_name: str = os.getenv(
        "VAIRRIEN_MODEL_NAME",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
    )

    model_api_url: str = os.getenv(
        "VAIRRIEN_MODEL_API_URL",
        "",
    )

    model_api_key: str = os.getenv(
        "VAIRRIEN_MODEL_API_KEY",
        "",
    )

    # ========================================================
    # VISION MODEL
    # ========================================================

    vision_provider: str = os.getenv(
        "VAIRRIEN_VISION_PROVIDER",
        "openrouter",
    )

    vision_model_name: str = os.getenv(
        "VAIRRIEN_VISION_MODEL_NAME",
        "",
    )

    vision_api_url: str = os.getenv(
        "VAIRRIEN_VISION_API_URL",
        "",
    )

    vision_api_key: str = os.getenv(
        "VAIRRIEN_VISION_API_KEY",
        "",
    )

    # ========================================================
    # API SERVER
    # ========================================================

    api_host: str = os.getenv(
        "VAIRRIEN_API_HOST",
        "0.0.0.0",
    )

    api_port: int = int(
        os.getenv(
            "VAIRRIEN_API_PORT",
            "8000",
        )
    )


settings = Settings()
