from __future__ import annotations

from os import PathLike

from ...errors import OptionalDependencyError
from ..core import DEFAULT_PLAYBACK_BLOCK_FRAMES, DEFAULT_VOLUME_PERCENT, PlaybackSession


PathInput = str | PathLike[str]


class SoundDeviceSink:
    def __init__(self) -> None:
        self._stream = None

    def open(self, *, sample_rate: int, channels: int) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise OptionalDependencyError(
                "sounddevice backend requires the optional 'playback' extra"
            ) from exc

        self._stream = sd.RawOutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
        )
        self._stream.start()

    def write(self, chunk: bytes) -> None:
        if self._stream is None:
            raise RuntimeError("sounddevice sink is not open")
        self._stream.write(chunk)

    def close(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None


def create_sounddevice_session(
    source_path: PathInput,
    *,
    volume_percent: float = DEFAULT_VOLUME_PERCENT,
    block_frames: int = DEFAULT_PLAYBACK_BLOCK_FRAMES,
) -> PlaybackSession:
    return PlaybackSession(
        source_path,
        sink=SoundDeviceSink(),
        volume_percent=volume_percent,
        block_frames=block_frames,
    )
