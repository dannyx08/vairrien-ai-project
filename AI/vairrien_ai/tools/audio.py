from __future__ import annotations

from typing import Any

from vairrien_ai.audio.engine import AudioEngine


class AudioTool:
    """
    Native Vairrien audio capability.

    Uses Vairrien's local audio engine for:
    - speech transcription
    - language detection
    - timestamped segments
    - audio file understanding preparation

    The audio engine is loaded lazily so importing the Vairrien
    server does not immediately load the Whisper model into memory.
    """

    def __init__(
        self,
        engine: AudioEngine | None = None,
    ):
        self._engine = engine

    def _get_engine(self) -> AudioEngine:
        """
        Create the audio engine only when audio transcription
        is actually requested.
        """
        if self._engine is None:
            self._engine = AudioEngine(
                model_size="small",
                device="cpu",
                compute_type="int8",
            )

        return self._engine

    async def transcribe_audio(
        self,
        file_path: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        if not file_path or not file_path.strip():
            return {
                "status": "error",
                "error": "No audio file path was provided.",
            }

        try:
            engine = self._get_engine()

            return engine.transcribe(
                file_path=file_path,
                language=language,
            )

        except Exception as error:
            return {
                "status": "error",
                "error": str(error),
            }