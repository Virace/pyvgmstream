from __future__ import annotations


class StreamHandle:
    def __init__(self, native_handle: object) -> None:
        self._native_handle = native_handle

    @property
    def sample_rate(self) -> int:
        return self._native_handle.sample_rate

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

    def read_pcm16(self, frame_count: int) -> bytes:
        return self._native_handle.read_pcm16(frame_count)

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
