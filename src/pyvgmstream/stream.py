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
