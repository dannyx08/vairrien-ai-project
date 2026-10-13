from __future__ import annotations

from typing import Any

from vairrien_ai.multimodal.inference import MultimodalInference


class MultimodalTool:
    """
    Tool adapter for Vairrien's multimodal inference capability.

    This layer exposes image, audio, and video understanding to
    Vairrien's ToolRegistry.

    The inference layer remains responsible for communicating with
    the configured multimodal model/provider.
    """

    def __init__(
        self,
        inference: MultimodalInference | None = None,
    ):
        self.inference = inference or MultimodalInference()

    async def understand_image(
        self,
        file_path: str,
        instruction: str,
    ) -> dict[str, Any]:
        """
        Understand and analyze an image.
        """

        if not file_path or not file_path.strip():
            return {
                "status": "error",
                "error": "No image file path was provided.",
            }

        if not instruction or not instruction.strip():
            return {
                "status": "error",
                "error": (
                    "No image understanding instruction "
                    "was provided."
                ),
            }

        try:
            return await self.inference.understand_image(
                file_path=file_path,
                instruction=instruction,
            )

        except Exception as error:
            return {
                "status": "error",
                "error": str(error),
            }

    async def understand_audio(
        self,
        file_path: str,
        instruction: str,
    ) -> dict[str, Any]:
        """
        Understand and analyze an audio file.
        """

        if not file_path or not file_path.strip():
            return {
                "status": "error",
                "error": "No audio file path was provided.",
            }

        if not instruction or not instruction.strip():
            return {
                "status": "error",
                "error": (
                    "No audio understanding instruction "
                    "was provided."
                ),
            }

        try:
            return await self.inference.understand_audio(
                file_path=file_path,
                instruction=instruction,
            )

        except Exception as error:
            return {
                "status": "error",
                "error": str(error),
            }

    async def understand_video(
        self,
        file_path: str,
        instruction: str,
    ) -> dict[str, Any]:
        """
        Understand and analyze a video file.
        """

        if not file_path or not file_path.strip():
            return {
                "status": "error",
                "error": "No video file path was provided.",
            }

        if not instruction or not instruction.strip():
            return {
                "status": "error",
                "error": (
                    "No video understanding instruction "
                    "was provided."
                ),
            }

        try:
            return await self.inference.understand_video(
                file_path=file_path,
                instruction=instruction,
            )

        except Exception as error:
            return {
                "status": "error",
                "error": str(error),
            }