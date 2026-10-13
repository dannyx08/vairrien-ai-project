from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

import requests

from vairrien_ai.config.settings import settings


class MultimodalInference:
    """
    Vairrien's image inference layer.

    This layer is responsible for remote multimodal image
    perception only.

    Architecture:

        Image
          ↓
        Vairrien MultimodalInference
          ↓
        OpenRouter
          ↓
        Configured vision model

    Audio is handled natively by Vairrien's AudioEngine.

    Video is handled natively by Vairrien's VideoEngine,
    which uses FFmpeg, AudioEngine, and this image layer
    for selected video frames.

    The orchestrator remains responsible for reasoning,
    planning, tool selection, and deciding what to do
    with the returned perception.
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    IMAGE_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
    ):
        self.model_name = (
            model_name
            or settings.vision_model_name
        )

        self.api_key = (
            api_key
            or settings.vision_api_key
            or os.getenv("OPENROUTER_API_KEY")
        )

        if not self.model_name:
            raise RuntimeError(
                "No multimodal image model is configured."
            )

        if not self.api_key:
            raise RuntimeError(
                "No OpenRouter API key is configured."
            )

    # ------------------------------------------------------------------
    # File helpers
    # ------------------------------------------------------------------

    def _read_file(
        self,
        file_path: str,
    ) -> tuple[Path, str, bytes]:
        """
        Validate and read a local image file.
        """

        if not file_path or not file_path.strip():
            raise ValueError(
                "No image file path was provided."
            )

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image file does not exist: {file_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Image path is not a file: {file_path}"
            )

        mime_type, _ = mimetypes.guess_type(
            path.name
        )

        if not mime_type:
            raise ValueError(
                f"Could not determine image type: {file_path}"
            )

        if mime_type not in self.IMAGE_TYPES:
            raise ValueError(
                "Unsupported image type. "
                "Supported types: JPEG, PNG, WEBP, GIF."
            )

        return path, mime_type, path.read_bytes()

    def _image_to_data_url(
        self,
        file_path: str,
    ) -> str:
        """
        Convert a local image into a base64 data URL.
        """

        _, mime_type, data = self._read_file(
            file_path
        )

        encoded = base64.b64encode(
            data
        ).decode("utf-8")

        return (
            f"data:{mime_type};base64,{encoded}"
        )

    # ------------------------------------------------------------------
    # Provider request
    # ------------------------------------------------------------------

    async def _request(
        self,
        content: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Send an image-capable request to OpenRouter.

        The method deliberately preserves provider diagnostics
        instead of hiding an empty or malformed response.
        """

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": (
                        f"Bearer {self.api_key}"
                    ),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=180,
            )

        except requests.RequestException as error:
            raise RuntimeError(
                f"Multimodal API network error: {error}"
            ) from error

        # --------------------------------------------------------------
        # Provider HTTP errors
        # --------------------------------------------------------------

        if not response.ok:
            try:
                error_data = response.json()
            except ValueError:
                error_data = response.text

            raise RuntimeError(
                "Multimodal API request failed "
                f"(HTTP {response.status_code}): "
                f"{error_data}"
            )

        # --------------------------------------------------------------
        # JSON decoding
        # --------------------------------------------------------------

        try:
            data = response.json()

        except ValueError as error:
            raise RuntimeError(
                "Multimodal API returned invalid JSON. "
                f"Raw response: {response.text[:4000]}"
            ) from error

        # --------------------------------------------------------------
        # Provider-level error object
        # --------------------------------------------------------------

        provider_error = data.get("error")

        if provider_error:
            raise RuntimeError(
                "Multimodal provider returned an error: "
                f"{provider_error}"
            )

        # --------------------------------------------------------------
        # Choices
        # --------------------------------------------------------------

        choices = data.get("choices")

        if not isinstance(choices, list):
            raise RuntimeError(
                "Multimodal API returned an invalid "
                f"'choices' field. "
                f"Raw response: {data}"
            )

        if not choices:
            raise RuntimeError(
                "Multimodal API returned no choices. "
                f"Model: {self.model_name}. "
                f"Raw response: {data}"
            )

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise RuntimeError(
                "Multimodal API returned an invalid choice: "
                f"{first_choice}"
            )

        message = first_choice.get(
            "message"
        )

        if not isinstance(message, dict):
            raise RuntimeError(
                "Multimodal API choice contained no valid "
                f"message. Raw choice: {first_choice}"
            )

        result_content = message.get(
            "content"
        )

        # Some providers may return null content while still
        # providing a refusal or another message field.
        if result_content is None:
            result_content = ""

        if isinstance(result_content, list):
            # Preserve structured provider content instead of
            # destroying it by converting it immediately to text.
            normalized_content: Any = result_content
        else:
            normalized_content = str(
                result_content
            )

        return {
            "status": "success",
            "model": data.get(
                "model",
                self.model_name,
            ),
            "content": normalized_content,
            "finish_reason": first_choice.get(
                "finish_reason"
            ),
            "usage": data.get(
                "usage"
            ),
            "id": data.get(
                "id"
            ),
        }

    # ------------------------------------------------------------------
    # Public image capability
    # ------------------------------------------------------------------

    async def understand_image(
        self,
        file_path: str,
        instruction: str,
    ) -> dict[str, Any]:
        """
        Analyze a local image using the configured
        online multimodal model.
        """

        if not instruction or not instruction.strip():
            raise ValueError(
                "No image understanding instruction was provided."
            )

        image_url = self._image_to_data_url(
            file_path
        )

        return await self._request(
            [
                {
                    "type": "text",
                    "text": instruction,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                    },
                },
            ]
        )
