from __future__ import annotations

from pathlib import Path
from typing import Any

from vairrien_ai.audio.transcription import AudioTranscriber
from vairrien_ai.audio.vad import AudioVAD


class AudioEngine:
    """
    Main Vairrien local audio engine.

    Responsibilities:
    - validate audio files
    - transcribe speech locally
    - detect language
    - preserve timestamps
    - optionally apply voice-activity filtering
    - return structured audio understanding data
    """

    SUPPORTED_EXTENSIONS = {
        ".wav",
        ".mp3",
        ".m4a",
        ".aac",
        ".ogg",
        ".flac",
        ".opus",
        ".wma",
        ".webm",
    }

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        vad_filter: bool = False,
    ):
        self.vad = AudioVAD(enabled=vad_filter)

        self.transcriber = AudioTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            vad_filter=vad_filter,
        )

    def validate_file(self, file_path: str) -> Path:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Audio path is not a file: {path}"
            )

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported audio format: {path.suffix}"
            )

        return path

    def transcribe(
        self,
        file_path: str,
        language: str | None = None,
    ) -> dict[str, Any]:
        path = self.validate_file(file_path)

        result = self.transcriber.transcribe(
            file_path=str(path),
            language=language,
        )

        return {
            "status": "success",
            "type": "audio_transcription",
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
            "transcription": result.to_dict(),
            "vad": self.vad.configuration(),
        }