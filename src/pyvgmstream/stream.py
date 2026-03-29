"""解码流句柄包装。"""

from __future__ import annotations

from .models import SampleFormat


class StreamHandle:
    """面向 Python 的解码流句柄薄包装。"""

    def __init__(self, native_handle: object) -> None:
        self._native_handle = native_handle

    @property
    def sample_rate(self) -> int:
        return self._native_handle.sample_rate

    @property
    def sample_format(self) -> SampleFormat:
        """返回当前输出缓冲区的采样格式。"""

        return SampleFormat(self._native_handle.sample_format)

    @property
    def sample_size(self) -> int:
        """返回单个采样占用的字节数。"""

        return self._native_handle.sample_size

    @property
    def channels(self) -> int:
        return self._native_handle.channels

    @property
    def input_channels(self) -> int:
        return self._native_handle.input_channels

    @property
    def channel_layout(self) -> int:
        return self._native_handle.channel_layout

    @property
    def stream_samples(self) -> int:
        return self._native_handle.stream_samples

    @property
    def play_samples(self) -> int:
        return self._native_handle.play_samples

    @property
    def duration_seconds(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return self.play_samples / self.sample_rate

    @property
    def stream_bitrate(self) -> int:
        return self._native_handle.stream_bitrate

    @property
    def loop_start(self) -> int:
        return self._native_handle.loop_start

    @property
    def loop_end(self) -> int:
        return self._native_handle.loop_end

    @property
    def play_forever(self) -> bool:
        return self._native_handle.play_forever

    @property
    def done(self) -> bool:
        return self._native_handle.done

    def read_frames(self, frame_count: int) -> bytes:
        """读取当前输出格式的交错音频帧。

        Args:
            frame_count: 希望读取的帧数。

        Returns:
            bytes: 当前流输出格式对应的原始帧数据。
        """

        return self._native_handle.read_frames(frame_count)

    def read_pcm16(self, frame_count: int) -> bytes:
        """读取 PCM16 帧数据便捷层。

        Args:
            frame_count: 希望读取的帧数。

        Returns:
            bytes: PCM16 交错帧数据。

        Raises:
            ValueError: 当前流输出格式不是 PCM16。
        """

        if self.sample_format is not SampleFormat.PCM16:
            raise ValueError(
                "current stream format is not PCM16; "
                "use read_frames() or request PCM16 explicitly via DecodeConfig"
            )
        return self.read_frames(frame_count)

    def tell_samples(self) -> int:
        return self._native_handle.tell_samples()

    def tell_seconds(self) -> float:
        if self.sample_rate <= 0:
            return 0.0
        return self.tell_samples() / self.sample_rate

    def seek_samples(self, position: int) -> None:
        self._native_handle.seek_samples(position)

    def seek_seconds(self, position: float) -> None:
        self.seek_samples(int(position * self.sample_rate))

    def reset(self) -> None:
        self._native_handle.reset()

    def close(self) -> None:
        self._native_handle.close()

    def __enter__(self) -> StreamHandle:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
