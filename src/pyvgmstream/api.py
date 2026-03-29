from __future__ import annotations

import io
import wave
from os import fspath
from os import PathLike
from pathlib import Path

from .models import DecodeResult, StreamInfo
from .stream import StreamHandle

PathInput = str | PathLike[str]


def probe(path: PathInput, *, subsong: int = 0) -> object:
    """读取当前后端返回的流元信息。"""
    from . import _native

    native_result = _native.probe(fspath(path), subsong)
    return StreamInfo(
        source_path=native_result["source_path"],
        subsong=native_result["subsong"],
        backend_name=native_result["backend_name"],
        sample_rate=native_result["sample_rate"],
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


def open_stream(path: PathInput, *, subsong: int = 0, config: object | None = None) -> object:
    """从当前后端打开一个 PCM16 解码流。"""
    del config

    from . import _native

    return StreamHandle(_native.NativeStreamHandle(fspath(path), subsong))


def decode_to_wav_file(
    in_path: PathInput,
    out_path: PathInput,
    *,
    config: object | None = None,
) -> object:
    """解码输入音频并导出为 WAV 文件。"""
    del config

    wav_payload, sample_rate, channels, frame_count = _decode_wav_payload(in_path)
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


def decode_to_wav_bytes(path: PathInput, *, config: object | None = None) -> bytes:
    """解码输入音频并导出为 WAV 字节。"""
    del config

    wav_payload, _sample_rate, _channels, _frame_count = _decode_wav_payload(path)
    return wav_payload


def _decode_wav_payload(path: PathInput) -> tuple[bytes, int, int, int]:
    with open_stream(path) as stream:
        buffer = io.BytesIO()
        total_frames = 0
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(stream.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(stream.sample_rate)

            while True:
                chunk = stream.read_pcm16(4096)
                if chunk:
                    wav_file.writeframes(chunk)
                    total_frames += len(chunk) // (stream.channels * 2)
                if stream.done:
                    break

        return buffer.getvalue(), stream.sample_rate, stream.channels, total_frames
