from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import islice
from os import PathLike
import os
from pathlib import Path
from typing import Iterable
import wave

from .api import open_stream
from .models import DecodeResult


PathInput = str | PathLike[str]
DEFAULT_CHUNK_FRAMES = 65536
DEFAULT_MAX_WORKERS = min(os.cpu_count() or 1, 8)
DEFAULT_DISPATCH_CHUNKSIZE = 64


@dataclass(frozen=True, slots=True)
class BatchTranscodeItemResult:
    source_path: Path
    output_path: Path
    frame_count: int
    byte_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


@dataclass(frozen=True, slots=True)
class BatchTranscodeSummary:
    input_root: Path | None
    output_root: Path | None
    processed_count: int
    failed_count: int
    results: tuple[BatchTranscodeItemResult, ...]

    @property
    def success_count(self) -> int:
        return self.processed_count - self.failed_count


def resolve_root(path_text: PathInput) -> Path:
    return Path(path_text).expanduser().resolve()


def iter_sources(input_root: Path, pattern: str = "*.wem") -> Iterable[Path]:
    yield from input_root.rglob(pattern)


def build_output_path(source_path: Path, input_root: Path | None, output_root: Path) -> Path:
    if input_root is None:
        return output_root / f"{source_path.stem}.wav"
    return (output_root / source_path.relative_to(input_root)).with_suffix(".wav")


def transcode_one(
    source_path: PathInput,
    output_path: PathInput,
    *,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
) -> DecodeResult:
    resolved_source = resolve_root(source_path)
    resolved_output = resolve_root(output_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    with open_stream(resolved_source) as stream, wave.open(str(resolved_output), "wb") as wav_file:
        sample_rate = stream.sample_rate
        channels = stream.channels

        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        total_frames = 0
        while not stream.done:
            chunk = stream.read_pcm16(chunk_frames)
            if not chunk:
                continue
            wav_file.writeframesraw(chunk)
            total_frames += len(chunk) // (channels * 2)

    return DecodeResult(
        output_path=resolved_output,
        sample_rate=sample_rate,
        channels=channels,
        frame_count=total_frames,
        byte_count=resolved_output.stat().st_size,
    )


def _run_transcode_job(job: tuple[str, str, str | None, int]) -> BatchTranscodeItemResult:
    source_text, output_root_text, input_root_text, chunk_frames = job
    source_path = Path(source_text)
    input_root = Path(input_root_text) if input_root_text is not None else None
    output_root = Path(output_root_text)
    output_path = build_output_path(source_path, input_root, output_root)

    try:
        result = transcode_one(source_path, output_path, chunk_frames=chunk_frames)
    except Exception as exc:
        return BatchTranscodeItemResult(
            source_path=source_path,
            output_path=output_path,
            frame_count=0,
            byte_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )

    return BatchTranscodeItemResult(
        source_path=source_path,
        output_path=result.output_path,
        frame_count=result.frame_count,
        byte_count=result.byte_count,
        error=None,
    )


def transcode_many(
    sources: Iterable[PathInput],
    output_root: PathInput,
    *,
    input_root: PathInput | None = None,
    workers: int = DEFAULT_MAX_WORKERS,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
    dispatch_chunksize: int = DEFAULT_DISPATCH_CHUNKSIZE,
) -> BatchTranscodeSummary:
    resolved_output_root = resolve_root(output_root)
    resolved_input_root = None if input_root is None else resolve_root(input_root)
    worker_count = max(int(workers), 1)
    resolved_chunk_frames = max(int(chunk_frames), 1)
    resolved_dispatch_chunksize = max(int(dispatch_chunksize), 1)

    jobs = [
        (
            str(resolve_root(source_path)),
            str(resolved_output_root),
            None if resolved_input_root is None else str(resolved_input_root),
            resolved_chunk_frames,
        )
        for source_path in sources
    ]

    if worker_count == 1:
        results_iter = map(_run_transcode_job, jobs)
    else:
        executor = ProcessPoolExecutor(max_workers=worker_count)
        try:
            results_iter = executor.map(
                _run_transcode_job,
                jobs,
                chunksize=resolved_dispatch_chunksize,
            )
            results = tuple(results_iter)
        finally:
            executor.shutdown()
        failed_count = sum(1 for result in results if not result.success)
        return BatchTranscodeSummary(
            input_root=resolved_input_root,
            output_root=resolved_output_root,
            processed_count=len(results),
            failed_count=failed_count,
            results=results,
        )

    results = tuple(results_iter)
    failed_count = sum(1 for result in results if not result.success)
    return BatchTranscodeSummary(
        input_root=resolved_input_root,
        output_root=resolved_output_root,
        processed_count=len(results),
        failed_count=failed_count,
        results=results,
    )


def transcode_tree(
    input_root: PathInput,
    output_root: PathInput,
    *,
    workers: int = DEFAULT_MAX_WORKERS,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
    dispatch_chunksize: int = DEFAULT_DISPATCH_CHUNKSIZE,
    limit: int | None = None,
    pattern: str = "*.wem",
) -> BatchTranscodeSummary:
    resolved_input_root = resolve_root(input_root)
    if not resolved_input_root.is_dir():
        raise FileNotFoundError(f"input root does not exist or is not a directory: {resolved_input_root}")

    source_iter = iter_sources(resolved_input_root, pattern=pattern)
    if limit is not None:
        source_iter = islice(source_iter, max(int(limit), 0))

    return transcode_many(
        source_iter,
        output_root,
        input_root=resolved_input_root,
        workers=workers,
        chunk_frames=chunk_frames,
        dispatch_chunksize=dispatch_chunksize,
    )
