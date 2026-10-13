from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

from vairrien_ai.audio.types import AudioSegment, AudioTranscription


class AudioTranscriber:
    """
    Local Vairrien speech-to-text engine.

    Uses faster-whisper for local transcription.
    No external transcription API is required.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        vad_filter: bool = False,
    ):
        self.model_size = model_size

        if device == "auto":
            device = "cuda"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        self.device = device
        self.compute_type = compute_type
        self.vad_filter = vad_filter

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(
        self,
        file_path: str,
        language: str | None = None,
        task: str = "transcribe",
    ) -> AudioTranscription:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Audio path is not a file: {path}"
            )

        segments, info = self.model.transcribe(
            str(path),
            language=language,
            task=task,
            vad_filter=self.vad_filter,
            word_timestamps=False,
        )

        output_segments: list[AudioSegment] = []
        text_parts: list[str] = []

        for segment in segments:
            text = segment.text.strip()

            if not text:
                continue

            output_segments.append(
                AudioSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                )
            )

            text_parts.append(text)

        full_text = " ".join(text_parts).strip()

        return AudioTranscription(
            text=full_text,
            language=getattr(info, "language", None),
            language_probability=getattr(
                info,
                "language_probability",
                None,
            ),
            duration=getattr(info, "duration", None),
            segments=output_segments,
            metadata={
                "model": self.model_size,
                "device": self.device,
                "compute_type": self.compute_type,
                "task": task,
                "vad_filter": self.vad_filter,
            },
        )