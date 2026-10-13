from __future__ import annotations


class AudioVAD:
    """
    Vairrien audio voice-activity abstraction.

    The initial implementation delegates speech filtering to the
    transcription engine's built-in VAD support.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def configuration(self) -> dict[str, bool]:
        return {
            "enabled": self.enabled,
        }