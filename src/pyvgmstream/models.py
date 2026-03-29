"""公开数据模型与采样格式枚举。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class SampleFormat(IntEnum):
    """解码流输出采样格式枚举。

    Attributes:
        PCM16: 16 位有符号整数 PCM。
        PCM24: 24 位整数 PCM。
        PCM32: 32 位有符号整数 PCM。
        FLOAT: 32 位浮点 PCM。
    """

    PCM16 = 1
    PCM24 = 2
    PCM32 = 3
    FLOAT = 4


@dataclass(frozen=True, slots=True)
class DecodeConfig:
    """控制解码输出语义的轻量配置。

    Attributes:
        sample_format: 若设置，则请求上游把输出缓冲区重映射为指定采样格式；
            若为 `None`，则保留上游默认输出格式。
        ignore_loop: 若设置，则显式覆盖上游 loop 处理策略；
            若为 `None`，则保留上游默认 loop 语义。
    """

    sample_format: SampleFormat | None = None
    ignore_loop: bool | None = None


@dataclass(frozen=True, slots=True)
class StreamInfo:
    """当前流的只读元信息投影。

    Attributes:
        source_path: 当前源文件路径。
        subsong: 当前加载的 subsong 编号。
        backend_name: 当前原生后端标识。
        sample_rate: 输出采样率。
        sample_format: 当前输出缓冲区的采样格式。
        sample_size: 单个采样占用的字节数。
        channels: 当前输出声道数。
        input_channels: 原始输入声道数。
        channel_layout: 输出声道布局位掩码。
        subsong_count: 当前文件包含的 subsong 总数。
        stream_samples: 原始流样本数。
        play_samples: 当前配置下的可播放样本数。
        duration_seconds: 当前配置下的总时长。
        stream_bitrate: 平均码率。
        loop_start: loop 起点样本位置。
        loop_end: loop 终点样本位置。
        loop_flag: 当前流是否带 loop。
        play_forever: 当前配置是否会无限循环。
        codec_name: 上游 codec 描述。
        layout_name: 上游 layout 描述。
        meta_name: 上游 meta 描述。
    """

    source_path: str
    subsong: int
    backend_name: str
    sample_rate: int
    sample_format: SampleFormat
    sample_size: int
    channels: int
    input_channels: int
    channel_layout: int
    subsong_count: int
    stream_samples: int
    play_samples: int
    duration_seconds: float
    stream_bitrate: int
    loop_start: int
    loop_end: int
    loop_flag: bool
    play_forever: bool
    codec_name: str
    layout_name: str
    meta_name: str


@dataclass(frozen=True, slots=True)
class DecodeResult:
    """WAV 导出结果摘要。

    Attributes:
        output_path: 导出后的 WAV 路径。
        sample_rate: 导出 WAV 的采样率。
        channels: 导出 WAV 的声道数。
        frame_count: 导出的总帧数。
        byte_count: 导出文件总字节数。
    """

    output_path: Path
    sample_rate: int
    channels: int
    frame_count: int
    byte_count: int
