from __future__ import annotations

from pathlib import Path
import time

from pyvgmstream import PCM16Sink, PlaybackSession, PlaybackState


class CollectingSink:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.delay_seconds = delay_seconds
        self.sample_rate: int | None = None
        self.channels: int | None = None
        self.total_bytes = 0
        self.write_count = 0
        self.closed = False

    def open(self, *, sample_rate: int, channels: int) -> None:
        self.sample_rate = sample_rate
        self.channels = channels

    def write(self, chunk: bytes) -> None:
        self.total_bytes += len(chunk)
        self.write_count += 1
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds)

    def close(self) -> None:
        self.closed = True


def wait_for(predicate, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")


def test_playback_session_matches_pcm16_sink_protocol() -> None:
    sink = CollectingSink()
    assert isinstance(sink, PCM16Sink)


def test_playback_session_streams_real_sample_and_finishes() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample = next(iter(sorted((repo_root / ".temp" / "wem").glob("*.wem"))), None)
    assert sample is not None

    sink = CollectingSink()
    session = PlaybackSession(sample, sink=sink, block_frames=256)
    session.start()

    assert session.wait(timeout=5.0) is True
    snapshot = session.snapshot()

    assert snapshot.state is PlaybackState.FINISHED
    assert snapshot.position_samples > 0
    assert snapshot.position_seconds >= 0.0
    assert sink.sample_rate == snapshot.sample_rate
    assert sink.channels == snapshot.channels
    assert sink.total_bytes > 0
    assert sink.closed is True


def test_playback_session_supports_pause_resume_and_stop() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample = next(iter(sorted((repo_root / ".temp" / "wem").glob("*.wem"))), None)
    assert sample is not None

    sink = CollectingSink(delay_seconds=0.002)
    session = PlaybackSession(sample, sink=sink, block_frames=16)
    session.start()

    wait_for(lambda: session.snapshot().position_samples > 0)
    session.pause()
    wait_for(lambda: session.snapshot().state is PlaybackState.PAUSED)

    paused_snapshot = session.snapshot()
    time.sleep(0.03)
    assert session.snapshot().position_samples == paused_snapshot.position_samples

    session.resume()
    wait_for(lambda: session.snapshot().state is PlaybackState.PLAYING)

    session.stop()
    assert session.snapshot().state is PlaybackState.STOPPED
    assert sink.closed is True
