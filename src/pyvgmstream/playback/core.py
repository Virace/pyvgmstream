from __future__ import annotations

from array import array
from dataclasses import dataclass
from enum import Enum
from os import PathLike
from pathlib import Path
from threading import Condition, Lock, Thread
from typing import Protocol, runtime_checkable

from ..api import open_stream
from ..errors import PyVGMStreamError


PathInput = str | PathLike[str]
DEFAULT_PLAYBACK_BLOCK_FRAMES = 4096
DEFAULT_VOLUME_PERCENT = 100.0


class PlaybackState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    source_path: Path
    state: PlaybackState
    position_samples: int
    position_seconds: float
    sample_rate: int
    channels: int
    done: bool
    recent_error: str | None


@runtime_checkable
class PCM16Sink(Protocol):
    def open(self, *, sample_rate: int, channels: int) -> None: ...

    def write(self, chunk: bytes) -> None: ...

    def close(self) -> None: ...


def scale_pcm16(chunk: bytes, volume_percent: float) -> bytes:
    if volume_percent >= 100.0:
        return chunk

    factor = max(volume_percent, 0.0) / 100.0
    samples = array("h")
    samples.frombytes(chunk)
    for index, value in enumerate(samples):
        scaled = int(value * factor)
        if scaled > 32767:
            scaled = 32767
        elif scaled < -32768:
            scaled = -32768
        samples[index] = scaled
    return samples.tobytes()


class PlaybackSession:
    def __init__(
        self,
        source_path: PathInput,
        *,
        sink: PCM16Sink,
        volume_percent: float = DEFAULT_VOLUME_PERCENT,
        block_frames: int = DEFAULT_PLAYBACK_BLOCK_FRAMES,
    ) -> None:
        self._source_path = Path(source_path).expanduser().resolve()
        self._sink = sink
        self._volume_percent = float(volume_percent)
        self._block_frames = max(int(block_frames), 1)

        self._condition = Condition()
        self._wait_lock = Lock()
        self._thread: Thread | None = None
        self._state = PlaybackState.IDLE
        self._position_samples = 0
        self._sample_rate = 0
        self._channels = 0
        self._done = False
        self._recent_error: str | None = None
        self._stop_requested = False
        self._pending_seek_samples: int | None = None

    def start(self) -> None:
        with self._condition:
            if self._thread is not None or self._state is not PlaybackState.IDLE:
                raise PyVGMStreamError("playback session has already been started")
            self._thread = Thread(target=self._run, name="pyvgmstream-playback", daemon=True)
            self._thread.start()

    def pause(self) -> None:
        with self._condition:
            if self._state is PlaybackState.PLAYING:
                self._state = PlaybackState.PAUSED

    def resume(self) -> None:
        with self._condition:
            if self._state is PlaybackState.PAUSED:
                self._state = PlaybackState.PLAYING
                self._condition.notify_all()

    def stop(self) -> None:
        thread: Thread | None
        with self._condition:
            self._stop_requested = True
            if self._state not in {PlaybackState.FINISHED, PlaybackState.ERROR}:
                self._state = PlaybackState.STOPPED
            self._condition.notify_all()
            thread = self._thread

        if thread is not None and thread.is_alive():
            thread.join()

    def close(self) -> None:
        self.stop()

    def wait(self, timeout: float | None = None) -> bool:
        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def seek_samples(self, position: int) -> None:
        with self._condition:
            self._pending_seek_samples = max(int(position), 0)
            self._condition.notify_all()

    def seek_seconds(self, position: float) -> None:
        sample_rate = self.snapshot().sample_rate
        self.seek_samples(int(max(position, 0.0) * sample_rate))

    def snapshot(self) -> PlaybackSnapshot:
        with self._wait_lock:
            sample_rate = self._sample_rate
            position_samples = self._position_samples
            state = self._state
            channels = self._channels
            done = self._done
            recent_error = self._recent_error

        position_seconds = 0.0 if sample_rate <= 0 else position_samples / sample_rate
        return PlaybackSnapshot(
            source_path=self._source_path,
            state=state,
            position_samples=position_samples,
            position_seconds=position_seconds,
            sample_rate=sample_rate,
            channels=channels,
            done=done,
            recent_error=recent_error,
        )

    def _run(self) -> None:
        try:
            with open_stream(self._source_path) as stream:
                with self._wait_lock:
                    self._sample_rate = stream.sample_rate
                    self._channels = stream.channels
                    self._state = PlaybackState.PLAYING

                self._sink.open(sample_rate=stream.sample_rate, channels=stream.channels)

                while True:
                    with self._condition:
                        while self._state is PlaybackState.PAUSED and not self._stop_requested:
                            self._condition.wait()

                        if self._stop_requested:
                            break

                        pending_seek_samples = self._pending_seek_samples
                        self._pending_seek_samples = None

                    if pending_seek_samples is not None:
                        stream.seek_samples(pending_seek_samples)
                        with self._wait_lock:
                            self._position_samples = stream.tell_samples()

                    if stream.done:
                        with self._wait_lock:
                            self._done = True
                            self._state = PlaybackState.FINISHED
                        break

                    chunk = stream.read_pcm16(self._block_frames)
                    with self._wait_lock:
                        self._position_samples = stream.tell_samples()

                    if not chunk:
                        continue

                    self._sink.write(scale_pcm16(chunk, self._volume_percent))

                    if stream.done:
                        with self._wait_lock:
                            self._done = True
                            self._state = PlaybackState.FINISHED
                        break
        except Exception as exc:
            with self._wait_lock:
                self._state = PlaybackState.ERROR
                self._recent_error = f"{type(exc).__name__}: {exc}"
        finally:
            self._sink.close()
            with self._wait_lock:
                if self._state is PlaybackState.PLAYING and self._stop_requested:
                    self._state = PlaybackState.STOPPED
                self._thread = None
