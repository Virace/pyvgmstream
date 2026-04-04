from __future__ import annotations

import threading
from pathlib import Path

import pyvgmstream.transcode as transcode_mod
from pyvgmstream import (
    BatchTranscodeItemResult,
    BatchTranscodeProgress,
    BatchTranscodeSummary,
    SampleFormat,
    open_stream,
    transcode_many,
    transcode_tree,
)
from tests.wav_header import inspect_wav_file


def test_transcode_tree_returns_summary_and_writes_wav(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    input_root = repo_root / ".temp" / "wem"
    output_root = tmp_path / "wav-out"
    source_path = next(iter(sorted(input_root.glob("*.wem"))), None)
    assert source_path is not None

    with open_stream(source_path) as stream:
        expected_sample_rate = stream.sample_rate
        expected_channels = stream.channels
        expected_sample_format = stream.sample_format
        expected_sample_size = stream.sample_size

    summary = transcode_tree(input_root, output_root, workers=1, limit=1)

    assert isinstance(summary, BatchTranscodeSummary)
    assert summary.processed_count == 1
    assert summary.failed_count == 0
    assert len(summary.results) == 1
    assert summary.results[0].success is True
    assert summary.results[0].output_path.is_file()
    header = inspect_wav_file(summary.results[0].output_path)
    expected_format_code = 3 if expected_sample_format is SampleFormat.FLOAT else 1
    assert header["format_code"] == expected_format_code
    assert header["sample_rate"] == expected_sample_rate
    assert header["channels"] == expected_channels
    assert header["bits_per_sample"] == expected_sample_size * 8
    assert header["data_size"] > 0


def test_transcode_tree_preserves_relative_layout(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sample = next(iter(sorted((repo_root / ".temp" / "wem").glob("*.wem"))), None)
    assert sample is not None

    input_root = tmp_path / "nested-in"
    nested_dir = input_root / "角色" / "皮肤" / "SFX"
    nested_dir.mkdir(parents=True)
    nested_sample = nested_dir / "样本.wem"
    nested_sample.write_bytes(sample.read_bytes())

    output_root = tmp_path / "nested-out"
    summary = transcode_tree(input_root, output_root, workers=1)

    assert summary.processed_count == 1
    assert summary.failed_count == 0
    expected_output = output_root / "角色" / "皮肤" / "SFX" / "样本.wav"
    assert summary.results[0].output_path == expected_output
    assert expected_output.is_file()


def test_transcode_many_reports_progress_snapshot(tmp_path: Path, monkeypatch) -> None:
    source_a = tmp_path / "a.wem"
    source_b = tmp_path / "b.wem"
    source_a.write_bytes(b"a")
    source_b.write_bytes(b"b")
    output_root = tmp_path / "progress-out"
    seen: list[BatchTranscodeProgress] = []
    notified = threading.Event()

    def fake_run(job: tuple[str, str, str | None, int, int]) -> BatchTranscodeItemResult:
        source_text, output_root_text, _input_root_text, _chunk_frames, _sample_format_value = job
        source_path = Path(source_text)
        output_path = Path(output_root_text) / f"{source_path.stem}.wav"
        if source_path.name == "b.wem":
            return BatchTranscodeItemResult(
                source_path=source_path,
                output_path=output_path,
                frame_count=0,
                byte_count=0,
                error="RuntimeError: boom",
            )
        return BatchTranscodeItemResult(
            source_path=source_path,
            output_path=output_path,
            frame_count=12,
            byte_count=48,
            error=None,
        )

    def on_progress(progress: BatchTranscodeProgress) -> None:
        seen.append(progress)
        if progress.completed_count == 2:
            notified.set()

    monkeypatch.setattr(transcode_mod, "_run_transcode_job", fake_run)

    summary = transcode_many(
        [source_a, source_b],
        output_root,
        workers=1,
        progress_callback=on_progress,
    )

    assert notified.wait(timeout=1.0)
    assert summary.processed_count == 2
    assert summary.failed_count == 1
    assert [(item.completed_count, item.total_count, item.failed_count) for item in seen] == [
        (1, 2, 0),
        (2, 2, 1),
    ]


def test_transcode_many_does_not_block_on_progress_callback(tmp_path: Path, monkeypatch) -> None:
    source_path = tmp_path / "slow.wem"
    source_path.write_bytes(b"slow")
    output_root = tmp_path / "slow-out"
    callback_started = threading.Event()
    callback_release = threading.Event()
    transcode_done = threading.Event()
    errors: list[Exception] = []
    summaries: list[BatchTranscodeSummary] = []

    def fake_run(job: tuple[str, str, str | None, int, int]) -> BatchTranscodeItemResult:
        source_text, output_root_text, _input_root_text, _chunk_frames, _sample_format_value = job
        source = Path(source_text)
        output_path = Path(output_root_text) / f"{source.stem}.wav"
        return BatchTranscodeItemResult(
            source_path=source,
            output_path=output_path,
            frame_count=4,
            byte_count=16,
            error=None,
        )

    def on_progress(_progress: BatchTranscodeProgress) -> None:
        callback_started.set()
        callback_release.wait(timeout=1.0)
        raise RuntimeError("progress callback boom")

    def run_transcode() -> None:
        try:
            summaries.append(
                transcode_many(
                    [source_path],
                    output_root,
                    workers=1,
                    progress_callback=on_progress,
                )
            )
        except Exception as exc:  # pragma: no cover - 回归测试要捕获任何泄漏异常
            errors.append(exc)
        finally:
            transcode_done.set()

    monkeypatch.setattr(transcode_mod, "_run_transcode_job", fake_run)

    thread = threading.Thread(target=run_transcode)
    thread.start()

    assert callback_started.wait(timeout=1.0)
    assert transcode_done.wait(timeout=0.3)
    assert not errors

    callback_release.set()
    thread.join(timeout=1.0)

    assert not errors
    assert summaries[0].processed_count == 1
    assert summaries[0].failed_count == 0


def test_transcode_tree_forwards_progress_callback(tmp_path: Path, monkeypatch) -> None:
    input_root = tmp_path / "tree-in"
    input_root.mkdir()
    output_root = tmp_path / "tree-out"
    seen: dict[str, object] = {}

    def on_progress(progress: BatchTranscodeProgress) -> BatchTranscodeProgress:
        return progress

    def fake_transcode_many(
        sources,
        output_root: Path,
        *,
        input_root: Path | None = None,
        workers: int = 1,
        chunk_frames: int = 0,
        dispatch_chunksize: int = 0,
        config=None,
        progress_callback=None,
    ) -> BatchTranscodeSummary:
        seen["sources"] = list(sources)
        seen["output_root"] = output_root
        seen["input_root"] = input_root
        seen["workers"] = workers
        seen["chunk_frames"] = chunk_frames
        seen["dispatch_chunksize"] = dispatch_chunksize
        seen["config"] = config
        seen["progress_callback"] = progress_callback
        return BatchTranscodeSummary(
            input_root=Path(input_root) if input_root is not None else None,
            output_root=Path(output_root),
            processed_count=0,
            failed_count=0,
            results=(),
        )

    monkeypatch.setattr(transcode_mod, "transcode_many", fake_transcode_many)

    summary = transcode_tree(input_root, output_root, progress_callback=on_progress)

    assert summary.processed_count == 0
    assert seen["progress_callback"] is on_progress
