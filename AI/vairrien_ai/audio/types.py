from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AudioSegment:
    start: float
    end: float
    text: str


@dataclass
class AudioTranscription:
    text: str
    language: str | None
    language_probability: float | None
    duration: float | None
    segments: list[AudioSegment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "language_probability": self.language_probability,
            "duration": self.duration,
            "segments": [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                }
                for segment in self.segments
            ],
            "metadata": self.metadata,
        }