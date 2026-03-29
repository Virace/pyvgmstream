"""`pyvgmstream` 的高层公开 API。"""

from __future__ import annotations

from os import fspath
from os import PathLike
from pathlib import Path

from ._wav import build_wav_payload
from .models import DecodeConfig, DecodeResult, SampleFormat, StreamInfo
from .stream import StreamHandle

PathInput = str | PathLike[str]
BufferInput = bytes | bytearray | memoryview


def probe(
    path: PathInput,
    *,
    subsong: int = 0,
    config: DecodeConfig | None = None,
) -> StreamInfo:
    """读取当前后端返回的流元信息。

    Args:
        path: 输入音频路径。
        subsong: 要读取的 subsong 编号，`0` 表示默认值。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        StreamInfo: 当前流的只读元信息。
    """

    from . import _native

    decode_config = _coerce_decode_config(config)
    native_sample_format = _resolve_native_sample_format(decode_config.sample_format)
    native_ignore_loop = _resolve_native_ignore_loop(decode_config.ignore_loop)
    native_result = _native.probe(fspath(path), subsong, native_sample_format, native_ignore_loop)
    return _build_stream_info(native_result)


def probe_buffer(
    data: BufferInput,
    *,
    filename_hint: str,
    subsong: int = 0,
    config: DecodeConfig | None = None,
) -> StreamInfo:
    """读取内存输入的流元信息。

    Args:
        data: 完整输入音频数据。
        filename_hint: 提供给上游的文件名提示，扩展名会参与格式判断。
        subsong: 要读取的 subsong 编号，`0` 表示默认值。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        StreamInfo: 当前流的只读元信息。
    """

    buffer_data = _coerce_buffer_input(data)
    resolved_filename_hint = _coerce_filename_hint(filename_hint)
    decode_config = _coerce_decode_config(config)
    native_sample_format = _resolve_native_sample_format(decode_config.sample_format)
    native_ignore_loop = _resolve_native_ignore_loop(decode_config.ignore_loop)
    from . import _native

    native_result = _native.probe_buffer(
        buffer_data,
        resolved_filename_hint,
        subsong,
        native_sample_format,
        native_ignore_loop,
    )
    return _build_stream_info(native_result)


def _build_stream_info(native_result: dict[str, object]) -> StreamInfo:
    """把 native probe 结果转换成公开数据模型。"""

    return StreamInfo(
        source_path=native_result["source_path"],
        subsong=native_result["subsong"],
        backend_name=native_result["backend_name"],
        sample_rate=native_result["sample_rate"],
        sample_format=SampleFormat(native_result["sample_format"]),
        sample_size=native_result["sample_size"],
        channels=native_result["channels"],
        input_channels=native_result["input_channels"],
        channel_layout=native_result["channel_layout"],
        subsong_count=native_result["subsong_count"],
        stream_samples=native_result["stream_samples"],
        play_samples=native_result["play_samples"],
        duration_seconds=native_result["duration_seconds"],
        stream_bitrate=native_result["stream_bitrate"],
        loop_start=native_result["loop_start"],
        loop_end=native_result["loop_end"],
        loop_flag=native_result["loop_flag"],
        play_forever=native_result["play_forever"],
        codec_name=native_result["codec_name"],
        layout_name=native_result["layout_name"],
        meta_name=native_result["meta_name"],
    )


def open_stream(
    path: PathInput,
    *,
    subsong: int = 0,
    config: DecodeConfig | None = None,
) -> StreamHandle:
    """从当前后端打开一个解码流。

    Args:
        path: 输入音频路径。
        subsong: 要打开的 subsong 编号，`0` 表示默认值。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        StreamHandle: 可持续读取当前输出格式帧数据的流句柄。

    Raises:
        TypeError: 传入了不受支持的配置对象。
    """

    from . import _native

    decode_config = _coerce_decode_config(config)
    native_sample_format = _resolve_native_sample_format(decode_config.sample_format)
    native_ignore_loop = _resolve_native_ignore_loop(decode_config.ignore_loop)
    return StreamHandle(
        _native.NativeStreamHandle(
            fspath(path),
            subsong,
            native_sample_format,
            native_ignore_loop,
        )
    )


def open_stream_from_buffer(
    data: BufferInput,
    *,
    filename_hint: str,
    subsong: int = 0,
    config: DecodeConfig | None = None,
) -> StreamHandle:
    """从内存输入打开一个解码流。

    Args:
        data: 完整输入音频数据。
        filename_hint: 提供给上游的文件名提示，扩展名会参与格式判断。
        subsong: 要打开的 subsong 编号，`0` 表示默认值。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        StreamHandle: 可持续读取当前输出格式帧数据的流句柄。
    """

    buffer_data = _coerce_buffer_input(data)
    resolved_filename_hint = _coerce_filename_hint(filename_hint)
    decode_config = _coerce_decode_config(config)
    native_sample_format = _resolve_native_sample_format(decode_config.sample_format)
    native_ignore_loop = _resolve_native_ignore_loop(decode_config.ignore_loop)
    from . import _native

    return StreamHandle(
        _native.NativeBufferStreamHandle(
            buffer_data,
            resolved_filename_hint,
            subsong,
            native_sample_format,
            native_ignore_loop,
        )
    )


def decode_to_wav_file(
    in_path: PathInput,
    out_path: PathInput,
    *,
    config: DecodeConfig | None = None,
) -> DecodeResult:
    """解码输入音频并导出为 WAV 文件。

    Args:
        in_path: 输入音频路径。
        out_path: 输出 WAV 路径。
        config: 可选的解码配置；若未设置，则保留上游当前输出采样格式。

    Returns:
        DecodeResult: 导出结果摘要。
    """

    wav_payload, sample_rate, channels, frame_count = _decode_wav_payload(in_path, config=config)
    output_path = Path(out_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(wav_payload)

    return DecodeResult(
        output_path=output_path,
        sample_rate=sample_rate,
        channels=channels,
        frame_count=frame_count,
        byte_count=output_path.stat().st_size,
    )


def decode_to_wav_bytes(path: PathInput, *, config: DecodeConfig | None = None) -> bytes:
    """解码输入音频并导出为 WAV 字节。

    Args:
        path: 输入音频路径。
        config: 可选的解码配置；若未设置，则保留上游当前输出采样格式。

    Returns:
        bytes: 完整 WAV 负载。
    """

    wav_payload, _sample_rate, _channels, _frame_count = _decode_wav_payload(path, config=config)
    return wav_payload


def decode_buffer_to_wav_file(
    data: BufferInput,
    out_path: PathInput,
    *,
    filename_hint: str,
    config: DecodeConfig | None = None,
) -> DecodeResult:
    """把内存输入解码并导出为 WAV 文件。

    Args:
        data: 完整输入音频数据。
        out_path: 输出 WAV 路径。
        filename_hint: 提供给上游的文件名提示，扩展名会参与格式判断。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        DecodeResult: 导出结果摘要。
    """

    wav_payload, sample_rate, channels, frame_count = _decode_buffer_to_wav_payload(
        data,
        filename_hint=filename_hint,
        config=config,
    )
    output_path = Path(out_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(wav_payload)

    return DecodeResult(
        output_path=output_path,
        sample_rate=sample_rate,
        channels=channels,
        frame_count=frame_count,
        byte_count=output_path.stat().st_size,
    )


def decode_buffer_to_wav_bytes(
    data: BufferInput,
    *,
    filename_hint: str,
    config: DecodeConfig | None = None,
) -> bytes:
    """把内存输入解码并导出为 WAV 字节。

    Args:
        data: 完整输入音频数据。
        filename_hint: 提供给上游的文件名提示，扩展名会参与格式判断。
        config: 可选的解码配置；若未设置，则保留上游默认语义。

    Returns:
        bytes: 完整 WAV 负载。
    """

    wav_payload, _sample_rate, _channels, _frame_count = _decode_buffer_to_wav_payload(
        data,
        filename_hint=filename_hint,
        config=config,
    )
    return wav_payload


def _decode_wav_payload(
    path: PathInput,
    *,
    config: DecodeConfig | None = None,
) -> tuple[bytes, int, int, int]:
    """把当前解码流打包成 WAV 负载。"""

    with open_stream(path, config=config) as stream:
        return _build_wav_payload_from_stream(stream)


def _decode_buffer_to_wav_payload(
    data: BufferInput,
    *,
    filename_hint: str,
    config: DecodeConfig | None = None,
) -> tuple[bytes, int, int, int]:
    """把内存输入流打包成 WAV 负载。"""

    with open_stream_from_buffer(data, filename_hint=filename_hint, config=config) as stream:
        return _build_wav_payload_from_stream(stream)


def _build_wav_payload_from_stream(stream: StreamHandle) -> tuple[bytes, int, int, int]:
    """从已打开的流读取完整 WAV 负载。"""

    payload = bytearray()
    total_frames = 0
    while True:
        chunk = stream.read_frames(4096)
        if chunk:
            payload.extend(chunk)
            total_frames += len(chunk) // (stream.channels * stream.sample_size)
        if stream.done:
            break

    wav_payload = build_wav_payload(
        sample_format=stream.sample_format,
        sample_rate=stream.sample_rate,
        channels=stream.channels,
        sample_size=stream.sample_size,
        frame_count=total_frames,
        pcm_payload=bytes(payload),
    )
    return wav_payload, stream.sample_rate, stream.channels, total_frames


def _coerce_decode_config(config: DecodeConfig | None) -> DecodeConfig:
    """标准化高层解码配置对象。"""

    if config is None:
        return DecodeConfig()
    if not isinstance(config, DecodeConfig):
        raise TypeError("config must be a DecodeConfig or None")
    return config


def _coerce_buffer_input(data: BufferInput) -> bytes:
    """把外部 bytes-like 输入标准化成原生层可消费的 bytes。"""

    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    raise TypeError("buffer input must be bytes-like")


def _coerce_filename_hint(filename_hint: str) -> str:
    """标准化内存输入的文件名提示。"""

    if not isinstance(filename_hint, str) or not filename_hint.strip():
        raise ValueError("filename_hint must be a non-empty string")
    return filename_hint


def _resolve_native_sample_format(sample_format: SampleFormat | None) -> int:
    """把公开采样格式枚举转换成 native bridge 所需值。"""

    if sample_format is None:
        return 0
    return int(sample_format)


def _resolve_native_ignore_loop(ignore_loop: bool | None) -> int:
    """把 tri-state loop 语义转换成 native bridge 所需值。"""

    if ignore_loop is None:
        return -1
    return int(ignore_loop)
