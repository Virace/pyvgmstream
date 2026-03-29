"""播放控制核心。

该模块只负责编排 `StreamHandle` 的读取、会话状态和 PCM16 sink 调度，
不直接绑定具体音频设备库。
"""

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
from ..models import DecodeConfig, SampleFormat


PathInput = str | PathLike[str]
DEFAULT_PLAYBACK_BLOCK_FRAMES = 4096
DEFAULT_VOLUME_PERCENT = 100.0


class PlaybackState(Enum):
    """播放会话的离散状态。"""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    FINISHED = "finished"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class PlaybackSnapshot:
    """当前播放会话的只读快照。

    这里同时保留当前位置和上游 `format` 中的静态元信息，
    方便下游一次性读取进度、总时长和基础格式字段。
    """

    source_path: Path
    state: PlaybackState
    position_samples: int
    position_seconds: float
    sample_rate: int
    channels: int
    input_channels: int
    channel_layout: int
    stream_samples: int
    play_samples: int
    duration_seconds: float
    stream_bitrate: int
    loop_start: int
    loop_end: int
    play_forever: bool
    done: bool
    recent_error: str | None


@runtime_checkable
class PCM16Sink(Protocol):
    """PCM16 输出后端协议。

    下游可以实现这个协议，把 `PlaybackSession` 接到任意音频库、
    网络输出或自定义消费端，而不是被固定在某个设备包上。
    """

    def open(self, *, sample_rate: int, channels: int) -> None: ...

    def write(self, chunk: bytes) -> None: ...

    def close(self) -> None: ...


def scale_pcm16(chunk: bytes, volume_percent: float) -> bytes:
    """对 PCM16 数据做简单线性音量缩放。"""

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
    """基于 `StreamHandle` 的本地播放控制会话。

    会话内部维护一个后台线程，负责读取 PCM16 数据并持续写入 sink。
    """

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
        self._input_channels = 0
        self._channel_layout = 0
        self._stream_samples = 0
        self._play_samples = 0
        self._stream_bitrate = 0
        self._loop_start = 0
        self._loop_end = 0
        self._play_forever = False
        self._done = False
        self._recent_error: str | None = None
        self._stop_requested = False
        self._pending_seek_samples: int | None = None

    def start(self) -> None:
        """启动后台播放线程。"""

        with self._condition:
            if self._thread is not None or self._state is not PlaybackState.IDLE:
                raise PyVGMStreamError("playback session has already been started")
            self._thread = Thread(target=self._run, name="pyvgmstream-playback", daemon=True)
            self._thread.start()

    def pause(self) -> None:
        """请求暂停当前会话。"""

        with self._condition:
            if self._state is PlaybackState.PLAYING:
                self._state = PlaybackState.PAUSED

    def resume(self) -> None:
        """恢复一个已暂停的会话。"""

        with self._condition:
            if self._state is PlaybackState.PAUSED:
                self._state = PlaybackState.PLAYING
                self._condition.notify_all()

    def stop(self) -> None:
        """停止当前会话并等待后台线程退出。"""

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
        """与 `stop()` 等价，便于作为显式资源释放入口。"""

        self.stop()

    def wait(self, timeout: float | None = None) -> bool:
        """等待后台线程结束。"""

        thread = self._thread
        if thread is None:
            return True
        thread.join(timeout=timeout)
        return not thread.is_alive()

    def seek_samples(self, position: int) -> None:
        """请求在后台线程中执行绝对样本位置跳转。"""

        with self._condition:
            self._pending_seek_samples = max(int(position), 0)
            self._condition.notify_all()

    def seek_seconds(self, position: float) -> None:
        """按秒数请求跳转。"""

        sample_rate = self.snapshot().sample_rate
        self.seek_samples(int(max(position, 0.0) * sample_rate))

    def snapshot(self) -> PlaybackSnapshot:
        """读取当前播放状态和元信息快照。"""

        with self._wait_lock:
            sample_rate = self._sample_rate
            position_samples = self._position_samples
            state = self._state
            channels = self._channels
            input_channels = self._input_channels
            channel_layout = self._channel_layout
            stream_samples = self._stream_samples
            play_samples = self._play_samples
            stream_bitrate = self._stream_bitrate
            loop_start = self._loop_start
            loop_end = self._loop_end
            play_forever = self._play_forever
            done = self._done
            recent_error = self._recent_error

        position_seconds = 0.0 if sample_rate <= 0 else position_samples / sample_rate
        duration_seconds = 0.0 if sample_rate <= 0 else play_samples / sample_rate
        return PlaybackSnapshot(
            source_path=self._source_path,
            state=state,
            position_samples=position_samples,
            position_seconds=position_seconds,
            sample_rate=sample_rate,
            channels=channels,
            input_channels=input_channels,
            channel_layout=channel_layout,
            stream_samples=stream_samples,
            play_samples=play_samples,
            duration_seconds=duration_seconds,
            stream_bitrate=stream_bitrate,
            loop_start=loop_start,
            loop_end=loop_end,
            play_forever=play_forever,
            done=done,
            recent_error=recent_error,
        )

    def _run(self) -> None:
        # 后台线程只做三件事：
        # 1. 打开解码流并初始化 sink；
        # 2. 在暂停/停止控制下持续读取 PCM16；
        # 3. 在退出时统一收口状态和资源。
        try:
            with open_stream(
                self._source_path,
                config=DecodeConfig(sample_format=SampleFormat.PCM16),
            ) as stream:
                with self._wait_lock:
                    self._sample_rate = stream.sample_rate
                    self._channels = stream.channels
                    self._input_channels = stream.input_channels
                    self._channel_layout = stream.channel_layout
                    self._stream_samples = stream.stream_samples
                    self._play_samples = stream.play_samples
                    self._stream_bitrate = stream.stream_bitrate
                    self._loop_start = stream.loop_start
                    self._loop_end = stream.loop_end
                    self._play_forever = stream.play_forever
                    self._state = PlaybackState.PLAYING

                self._sink.open(sample_rate=stream.sample_rate, channels=stream.channels)

                while True:
                    with self._condition:
                        # pause/seek/stop 都通过条件变量串到同一线程里，
                        # 避免下游在多线程间直接操作原生句柄。
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
