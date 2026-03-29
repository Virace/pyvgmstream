"""`sounddevice` 默认播放后端。"""

from __future__ import annotations

from os import PathLike

from ...errors import OptionalDependencyError
from ..core import DEFAULT_PLAYBACK_BLOCK_FRAMES, DEFAULT_VOLUME_PERCENT, PlaybackSession


PathInput = str | PathLike[str]


class SoundDeviceSink:
    """基于 `sounddevice.RawOutputStream` 的 PCM16 sink。"""

    def __init__(self) -> None:
        self._stream = None

    def open(self, *, sample_rate: int, channels: int) -> None:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise OptionalDependencyError(
                "sounddevice 后端需要安装可选的 playback extra"
            ) from exc

        self._stream = sd.RawOutputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
        )
        self._stream.start()

    def write(self, chunk: bytes) -> None:
        if self._stream is None:
            raise RuntimeError("sounddevice sink 尚未打开")
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
    """创建一个使用 `sounddevice` 后端的播放会话。"""

    return PlaybackSession(
        source_path,
        sink=SoundDeviceSink(),
        volume_percent=volume_percent,
        block_frames=block_frames,
    )
