from __future__ import annotations

import os
from typing import Any

import requests

from vairrien_ai.model.provider import ModelProvider


class OpenRouterProvider(ModelProvider):
    """
    OpenRouter model provider for Vairrien AI.

    Responsibilities:
    - Send chat messages to OpenRouter
    - Support normal text generation
    - Support OpenAI-compatible tool/function calling
    - Return structured responses to the orchestrator
    - Preserve tool calls and usage information
    - Validate and surface provider/API errors
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        model_name: str,
        api_key: str | None = None,
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set."
            )

    # ========================================================
    # GENERATION
    # ========================================================

    async def generate(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Generate a model response.

        IMPORTANT:
        This method returns the complete structured response,
        not just the text content.

        The orchestrator needs the structured response because
        the model may return tool_calls instead of text.
        """

        return await self.generate_response(
            messages=messages,
            **kwargs,
        )

    # ========================================================
    # STRUCTURED GENERATION
    # ========================================================

    async def generate_response(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Send a request to OpenRouter and normalize its response
        into the structure expected by VairrienOrchestrator.
        """

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }

        # Add optional provider parameters, including:
        # tools
        # temperature
        # max_tokens
        # tool_choice
        # etc.
        payload.update(kwargs)

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
                timeout=120,
            )

        except requests.RequestException as error:
            raise RuntimeError(
                f"OpenRouter network error: {error}"
            ) from error

        # ====================================================
        # HTTP ERROR
        # ====================================================

        if not response.ok:
            try:
                error_data = response.json()
            except ValueError:
                error_data = response.text

            raise RuntimeError(
                "OpenRouter API request failed "
                f"(HTTP {response.status_code}): "
                f"{error_data}"
            )

        # ====================================================
        # JSON PARSING
        # ====================================================

        try:
            data = response.json()

        except ValueError as error:
            raise RuntimeError(
                "OpenRouter returned invalid JSON. "
                f"Response: {response.text[:2000]}"
            ) from error

        # ====================================================
        # API-LEVEL ERROR
        # ====================================================

        if isinstance(data, dict) and data.get("error"):
            error_data = data["error"]

            if isinstance(error_data, dict):
                error_message = error_data.get(
                    "message",
                    str(error_data),
                )

                error_code = error_data.get(
                    "code"
                )

                if error_code is not None:
                    error_message = (
                        f"{error_message} "
                        f"(code: {error_code})"
                    )

            else:
                error_message = str(error_data)

            raise RuntimeError(
                "OpenRouter returned an API error: "
                f"{error_message}"
            )

        # ====================================================
        # RESPONSE VALIDATION
        # ====================================================

        if not isinstance(data, dict):
            raise RuntimeError(
                "OpenRouter returned an invalid response."
            )

        choices = data.get("choices")

        if not choices:
            raise RuntimeError(
                "OpenRouter returned no choices. "
                f"Response: {data}"
            )

        if not isinstance(choices, list):
            raise RuntimeError(
                "OpenRouter returned an invalid "
                "'choices' field. "
                f"Response: {data}"
            )

        first_choice = choices[0]

        if not isinstance(first_choice, dict):
            raise RuntimeError(
                "OpenRouter returned an invalid choice. "
                f"Response: {data}"
            )

        # ====================================================
        # ASSISTANT MESSAGE
        # ====================================================

        message = first_choice.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "OpenRouter response contained no valid "
                "assistant message. "
                f"Response: {data}"
            )

        # ====================================================
        # CONTENT
        # ====================================================

        content = message.get("content")

        # Some models may return no text when they are making
        # a tool call. That is valid and must NOT be treated
        # as an error.
        if content is not None and not isinstance(
            content,
            str,
        ):
            content = str(content)

        # ====================================================
        # TOOL CALLS
        # ====================================================

        tool_calls = message.get(
            "tool_calls",
            [],
        )

        if tool_calls is None:
            tool_calls = []

        if not isinstance(tool_calls, list):
            tool_calls = []

        # ====================================================
        # ROLE
        # ====================================================

        role = message.get(
            "role",
            "assistant",
        )

        # ====================================================
        # CHOICE METADATA
        # ====================================================

        finish_reason = first_choice.get(
            "finish_reason"
        )

        choice_index = first_choice.get(
            "index"
        )

        # ====================================================
        # NORMALIZED RESPONSE
        # ====================================================

        return {
            "content": content,
            "tool_calls": tool_calls,
            "role": role,
            "finish_reason": finish_reason,
            "choice_index": choice_index,
            "usage": data.get("usage"),
            "id": data.get("id"),
            "model": data.get(
                "model",
                self.model_name,
            ),
            "raw": message,
        }

    # ========================================================
    # HEALTH
    # ========================================================

    async def health(self) -> bool:
        """
        Basic provider configuration health check.
        """

        return bool(
            self.api_key
            and self.model_name
            and self.API_URL
        )