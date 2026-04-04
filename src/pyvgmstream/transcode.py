"""批量 WAV 转码能力。

该模块负责把目录扫描、多进程调度和单文件流式导出组合成稳定的
Python API，避免下游直接复用脚本逻辑。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import islice
from os import PathLike
import os
from pathlib import Path
from queue import SimpleQueue
from threading import Thread

from ._wav import write_wav_file
from .api import open_stream
from .models import DecodeConfig, DecodeResult, SampleFormat


PathInput = str | PathLike[str]
DEFAULT_CHUNK_FRAMES = 65536
DEFAULT_MAX_WORKERS = min(os.cpu_count() or 1, 8)
DEFAULT_DISPATCH_CHUNKSIZE = 64


@dataclass(frozen=True, slots=True)
class BatchTranscodeItemResult:
    """单个输入文件的转码结果。"""

    source_path: Path
    output_path: Path
    frame_count: int
    byte_count: int
    error: str | None = None

    @property
    def success(self) -> bool:
        """当前条目是否成功转码。"""

        return self.error is None


@dataclass(frozen=True, slots=True)
class BatchTranscodeProgress:
    """一批转码任务的进度快照。

    Attributes:
        completed_count: 已完成的条目数。
        total_count: 当前批次的总条目数。
        failed_count: 当前已失败的条目数。
    """

    completed_count: int
    total_count: int
    failed_count: int


ProgressCallback = Callable[[BatchTranscodeProgress], object]


@dataclass(frozen=True, slots=True)
class BatchTranscodeSummary:
    """一批转码任务的汇总结果。"""

    input_root: Path | None
    output_root: Path | None
    processed_count: int
    failed_count: int
    results: tuple[BatchTranscodeItemResult, ...]

    @property
    def success_count(self) -> int:
        """成功转码的条目数。"""

        return self.processed_count - self.failed_count


class _ProgressRelay:
    """异步转发进度回调。"""

    def __init__(self, callback: ProgressCallback | None) -> None:
        self._callback = callback
        self._queue: SimpleQueue[BatchTranscodeProgress | None] | None = None
        self._thread: Thread | None = None

        if callback is None:
            return

        self._queue = SimpleQueue()
        self._thread = Thread(
            target=self._run,
            name="pyvgmstream-transcode-progress",
            daemon=True,
        )
        self._thread.start()

    def notify(self, progress: BatchTranscodeProgress) -> None:
        """推送最新进度。"""

        if self._queue is None:
            return

        self._queue.put(progress)

    def close(self) -> None:
        """关闭进度转发器。"""

        if self._queue is None:
            return

        self._queue.put(None)

    def _run(self) -> None:
        """消费后台队列并调用用户回调。"""

        assert self._callback is not None
        assert self._queue is not None

        while True:
            progress = self._queue.get()
            if progress is None:
                return

            try:
                self._callback(progress)
            except Exception:
                continue


def resolve_root(path_text: PathInput) -> Path:
    """标准化外部传入路径。"""

    return Path(path_text).expanduser().resolve()


def iter_sources(input_root: Path, pattern: str = "*.wem") -> Iterable[Path]:
    """递归扫描输入目录下匹配的音频文件。"""

    yield from input_root.rglob(pattern)


def build_output_path(source_path: Path, input_root: Path | None, output_root: Path) -> Path:
    """根据输入根目录推导输出 WAV 路径。"""

    if input_root is None:
        return output_root / f"{source_path.stem}.wav"
    return (output_root / source_path.relative_to(input_root)).with_suffix(".wav")


def transcode_one(
    source_path: PathInput,
    output_path: PathInput,
    *,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
    config: DecodeConfig | None = None,
) -> DecodeResult:
    """把单个输入文件流式导出为 WAV。"""

    resolved_source = resolve_root(source_path)
    resolved_output = resolve_root(output_path)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    decode_config = config

    with open_stream(resolved_source, config=decode_config) as stream:
        sample_rate = stream.sample_rate
        channels = stream.channels
        sample_size = stream.sample_size
        sample_format = stream.sample_format
        payload = bytearray()
        total_frames = 0
        while not stream.done:
            chunk = stream.read_frames(chunk_frames)
            if not chunk:
                continue
            payload.extend(chunk)
            total_frames += len(chunk) // (channels * sample_size)

    write_wav_file(
        resolved_output,
        sample_format=sample_format,
        sample_rate=sample_rate,
        channels=channels,
        sample_size=sample_size,
        frame_count=total_frames,
        pcm_payload=bytes(payload),
    )

    return DecodeResult(
        output_path=resolved_output,
        sample_rate=sample_rate,
        channels=channels,
        frame_count=total_frames,
        byte_count=resolved_output.stat().st_size,
    )


def _run_transcode_job(job: tuple[str, str, str | None, int, int]) -> BatchTranscodeItemResult:
    """子进程序列化入口。"""

    source_text, output_root_text, input_root_text, chunk_frames, sample_format_value = job
    source_path = Path(source_text)
    input_root = Path(input_root_text) if input_root_text is not None else None
    output_root = Path(output_root_text)
    output_path = build_output_path(source_path, input_root, output_root)
    config = None if sample_format_value == 0 else DecodeConfig(sample_format=SampleFormat(sample_format_value))

    try:
        result = transcode_one(source_path, output_path, chunk_frames=chunk_frames, config=config)
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


def _collect_summary(
    results_iter: Iterable[BatchTranscodeItemResult],
    *,
    input_root: Path | None,
    output_root: Path,
    total_count: int,
    progress_callback: ProgressCallback | None,
) -> BatchTranscodeSummary:
    """消费结果迭代器并汇总最终状态。"""

    results: list[BatchTranscodeItemResult] = []
    failed_count = 0
    relay = _ProgressRelay(progress_callback)

    try:
        for completed_count, result in enumerate(results_iter, start=1):
            results.append(result)
            if not result.success:
                failed_count += 1

            relay.notify(
                BatchTranscodeProgress(
                    completed_count=completed_count,
                    total_count=total_count,
                    failed_count=failed_count,
                )
            )
    finally:
        relay.close()

    return BatchTranscodeSummary(
        input_root=input_root,
        output_root=output_root,
        processed_count=len(results),
        failed_count=failed_count,
        results=tuple(results),
    )


def transcode_many(
    sources: Iterable[PathInput],
    output_root: PathInput,
    *,
    input_root: PathInput | None = None,
    workers: int = DEFAULT_MAX_WORKERS,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
    dispatch_chunksize: int = DEFAULT_DISPATCH_CHUNKSIZE,
    config: DecodeConfig | None = None,
    progress_callback: ProgressCallback | None = None,
) -> BatchTranscodeSummary:
    """批量转码任意来源的输入文件列表。

    Args:
        sources: 待转码的输入文件路径序列。
        output_root: 输出 WAV 文件的根目录。
        input_root: 输入根目录。提供后会保留相对目录结构。
        workers: 转码使用的进程数。
        chunk_frames: 每次从流中读取的 PCM 帧数。
        dispatch_chunksize: 多进程派发时每批任务的块大小。
        config: 可选的解码配置。
        progress_callback: 异步接收进度快照的通知回调。回调异常不会中断转码。

    Returns:
        当前批次的转码汇总结果。
    """

    resolved_output_root = resolve_root(output_root)
    resolved_input_root = None if input_root is None else resolve_root(input_root)
    worker_count = max(int(workers), 1)
    resolved_chunk_frames = max(int(chunk_frames), 1)
    resolved_dispatch_chunksize = max(int(dispatch_chunksize), 1)
    decode_config = config

    # 先把输入标准化成可序列化的 job 列表，后续才能稳定交给多进程。
    jobs = [
        (
            str(resolve_root(source_path)),
            str(resolved_output_root),
            None if resolved_input_root is None else str(resolved_input_root),
            resolved_chunk_frames,
            0 if decode_config is None or decode_config.sample_format is None else int(decode_config.sample_format),
        )
        for source_path in sources
    ]
    total_count = len(jobs)

    if worker_count == 1:
        results_iter = map(_run_transcode_job, jobs)
        return _collect_summary(
            results_iter,
            input_root=resolved_input_root,
            output_root=resolved_output_root,
            total_count=total_count,
            progress_callback=progress_callback,
        )

    executor = ProcessPoolExecutor(max_workers=worker_count)
    try:
        results_iter = executor.map(
            _run_transcode_job,
            jobs,
            chunksize=resolved_dispatch_chunksize,
        )
        return _collect_summary(
            results_iter,
            input_root=resolved_input_root,
            output_root=resolved_output_root,
            total_count=total_count,
            progress_callback=progress_callback,
        )
    finally:
        executor.shutdown()


def transcode_tree(
    input_root: PathInput,
    output_root: PathInput,
    *,
    workers: int = DEFAULT_MAX_WORKERS,
    chunk_frames: int = DEFAULT_CHUNK_FRAMES,
    dispatch_chunksize: int = DEFAULT_DISPATCH_CHUNKSIZE,
    limit: int | None = None,
    pattern: str = "*.wem",
    config: DecodeConfig | None = None,
    progress_callback: ProgressCallback | None = None,
) -> BatchTranscodeSummary:
    """递归扫描目录并批量转码为 WAV。

    Args:
        input_root: 递归扫描的输入目录。
        output_root: 输出 WAV 文件的根目录。
        workers: 转码使用的进程数。
        chunk_frames: 每次从流中读取的 PCM 帧数。
        dispatch_chunksize: 多进程派发时每批任务的块大小。
        limit: 仅处理前 N 个匹配文件。
        pattern: 递归扫描时使用的 glob 模式。
        config: 可选的解码配置。
        progress_callback: 异步接收进度快照的通知回调。回调异常不会中断转码。

    Returns:
        当前批次的转码汇总结果。
    """

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
        config=config,
        progress_callback=progress_callback,
    )
