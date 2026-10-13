from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from vairrien_ai.audio import AudioEngine
from vairrien_ai.multimodal.inference import MultimodalInference


class VideoEngine:
    """
    Vairrien native video-processing engine.

    Responsibilities:
    - inspect video files with FFmpeg
    - extract representative video frames
    - extract audio when present
    - transcribe extracted audio with Vairrien's AudioEngine
    - send extracted frames to Vairrien's image multimodal model
    - combine the resulting media information

    Video processing itself does not depend on a hosted
    video-understanding API.
    """

    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
        ".avi",
        ".m4v",
        ".mpeg",
        ".mpg",
    }

    def __init__(
        self,
        multimodal: MultimodalInference | None = None,
        audio: AudioEngine | None = None,
        frame_count: int = 8,
    ):
        self.multimodal = (
            multimodal
            or MultimodalInference()
        )

        self.audio = audio

        if frame_count < 1:
            raise ValueError(
                "frame_count must be at least 1."
            )

        self.frame_count = frame_count

    # ========================================================
    # VALIDATION
    # ========================================================

    def _validate_video(
        self,
        file_path: str,
    ) -> Path:

        if not file_path or not file_path.strip():
            raise ValueError(
                "No video file path was provided."
            )

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Video file does not exist: {file_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Video path is not a file: {file_path}"
            )

        if path.suffix.lower() not in self.VIDEO_EXTENSIONS:
            raise ValueError(
                "Unsupported video format: "
                f"{path.suffix}"
            )

        return path

    # ========================================================
    # FFMPEG
    # ========================================================

    def _run_ffmpeg(
        self,
        arguments: list[str],
    ) -> subprocess.CompletedProcess[str]:

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            *arguments,
        ]

        try:
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )

        except FileNotFoundError as error:
            raise RuntimeError(
                "FFmpeg was not found. "
                "Make sure FFmpeg is installed and available "
                "from the system PATH."
            ) from error

        except subprocess.CalledProcessError as error:
            message = (
                error.stderr.strip()
                or "FFmpeg processing failed."
            )

            raise RuntimeError(
                message
            ) from error

    # ========================================================
    # INSPECTION
    # ========================================================

    def inspect(
        self,
        file_path: str,
    ) -> dict[str, Any]:

        path = self._validate_video(
            file_path
        )

        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )

        except FileNotFoundError as error:
            raise RuntimeError(
                "ffprobe was not found. "
                "Make sure FFmpeg is installed correctly."
            ) from error

        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                error.stderr.strip()
                or "Unable to inspect video."
            ) from error

        try:
            metadata = json.loads(
                result.stdout
            )
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "FFprobe returned invalid metadata."
            ) from error

        streams = metadata.get(
            "streams",
            [],
        )

        format_data = metadata.get(
            "format",
            {},
        )

        video_stream = next(
            (
                stream
                for stream in streams
                if stream.get("codec_type")
                == "video"
            ),
            None,
        )

        audio_stream = next(
            (
                stream
                for stream in streams
                if stream.get("codec_type")
                == "audio"
            ),
            None,
        )

        return {
            "status": "success",
            "file_name": path.name,
            "file_extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "duration": float(
                format_data.get(
                    "duration",
                    0,
                )
                or 0
            ),
            "bitrate": format_data.get(
                "bit_rate"
            ),
            "video": (
                {
                    "codec": video_stream.get(
                        "codec_name"
                    ),
                    "width": video_stream.get(
                        "width"
                    ),
                    "height": video_stream.get(
                        "height"
                    ),
                    "fps": self._fps(
                        video_stream
                    ),
                }
                if video_stream
                else None
            ),
            "audio": (
                {
                    "codec": audio_stream.get(
                        "codec_name"
                    ),
                    "sample_rate": audio_stream.get(
                        "sample_rate"
                    ),
                    "channels": audio_stream.get(
                        "channels"
                    ),
                }
                if audio_stream
                else None
            ),
        }

    def _fps(
        self,
        stream: dict[str, Any],
    ) -> float | None:

        value = stream.get(
            "r_frame_rate"
        )

        if not value or "/" not in value:
            return None

        numerator, denominator = value.split(
            "/",
            1,
        )

        try:
            return round(
                float(numerator)
                / float(denominator),
                3,
            )
        except (
            ValueError,
            ZeroDivisionError,
        ):
            return None

    # ========================================================
    # FRAME EXTRACTION
    # ========================================================

    def extract_frames(
        self,
        file_path: str,
        output_dir: str | None = None,
        frame_count: int | None = None,
    ) -> list[str]:

        path = self._validate_video(
            file_path
        )

        count = (
            frame_count
            if frame_count is not None
            else self.frame_count
        )

        if count < 1:
            raise ValueError(
                "frame_count must be at least 1."
            )

        metadata = self.inspect(
            str(path)
        )

        duration = float(
            metadata.get(
                "duration",
                0,
            )
        )

        if duration <= 0:
            raise RuntimeError(
                "Video duration could not be determined."
            )

        if output_dir:
            frame_dir = Path(
                output_dir
            )
            frame_dir.mkdir(
                parents=True,
                exist_ok=True,
            )
            cleanup = False
        else:
            frame_dir = Path(
                tempfile.mkdtemp(
                    prefix="vairrien_video_frames_"
                )
            )
            cleanup = False

        frame_paths: list[str] = []

        # Avoid sampling exactly at the first or last frame.
        if count == 1:
            timestamps = [
                duration / 2
            ]
        else:
            step = duration / (
                count + 1
            )

            timestamps = [
                step * index
                for index in range(
                    1,
                    count + 1,
                )
            ]

        for index, timestamp in enumerate(
            timestamps,
            start=1,
        ):

            output_path = (
                frame_dir
                / f"frame_{index:04d}.jpg"
            )

            self._run_ffmpeg(
                [
                    "-ss",
                    str(timestamp),
                    "-i",
                    str(path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    str(output_path),
                ]
            )

            if output_path.exists():
                frame_paths.append(
                    str(output_path)
                )

        if not frame_paths:
            raise RuntimeError(
                "FFmpeg could not extract any video frames."
            )

        return frame_paths

    # ========================================================
    # AUDIO EXTRACTION
    # ========================================================

    def extract_audio(
        self,
        file_path: str,
        output_path: str | None = None,
    ) -> str | None:

        path = self._validate_video(
            file_path
        )

        metadata = self.inspect(
            str(path)
        )

        if not metadata.get("audio"):
            return None

        if output_path:
            audio_path = Path(
                output_path
            )
        else:
            temp_dir = Path(
                tempfile.mkdtemp(
                    prefix="vairrien_video_audio_"
                )
            )

            audio_path = (
                temp_dir
                / "audio.wav"
            )

        self._run_ffmpeg(
            [
                "-i",
                str(path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-y",
                str(audio_path),
            ]
        )

        if not audio_path.exists():
            raise RuntimeError(
                "FFmpeg failed to extract the audio track."
            )

        return str(audio_path)

    # ========================================================
    # VISUAL UNDERSTANDING
    # ========================================================

    async def understand_frames(
        self,
        frame_paths: list[str],
        instruction: str,
    ) -> list[dict[str, Any]]:

        if not frame_paths:
            return []

        if not instruction.strip():
            raise ValueError(
                "No video understanding instruction was provided."
            )

        results = []

        for frame_path in frame_paths:

            result = (
                await self.multimodal
                .understand_image(
                    file_path=frame_path,
                    instruction=instruction,
                )
            )

            results.append(
                {
                    "frame": frame_path,
                    "result": result,
                }
            )

        return results

    # ========================================================
    # FULL VIDEO UNDERSTANDING
    # ========================================================

    async def understand(
        self,
        file_path: str,
        instruction: str,
        frame_count: int | None = None,
        transcribe_audio: bool = True,
    ) -> dict[str, Any]:

        path = self._validate_video(
            file_path
        )

        if not instruction.strip():
            raise ValueError(
                "No video understanding instruction was provided."
            )

        metadata = self.inspect(
            str(path)
        )

        frames = self.extract_frames(
            str(path),
            frame_count=frame_count,
        )

        visual_results = (
            await self.understand_frames(
                frame_paths=frames,
                instruction=instruction,
            )
        )

        audio_result = None

        if (
            transcribe_audio
            and metadata.get("audio")
        ):

            audio_path = self.extract_audio(
                str(path)
            )

            if audio_path:

                if self.audio is None:
                    self.audio = AudioEngine(
                        model_size="small",
                        device="cpu",
                        compute_type="int8",
                    )

                audio_result = (
                    self.audio.transcribe(
                        audio_path
                    )
                )

        return {
            "status": "success",
            "type": "video_understanding",
            "file_name": path.name,
            "metadata": metadata,
            "frames": {
                "count": len(frames),
                "paths": frames,
                "results": visual_results,
            },
            "audio": audio_result,
        }