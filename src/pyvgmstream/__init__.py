"""`pyvgmstream` 的公开 Python 包入口。"""

from .api import (
    decode_buffer_to_wav_bytes,
    decode_buffer_to_wav_file,
    decode_to_wav_bytes,
    decode_to_wav_file,
    open_stream,
    open_stream_from_buffer,
    probe,
    probe_buffer,
)
from .errors import PyVGMStreamError
from .log import LogLevel, disable_log_callback, set_log_callback
from .models import DecodeConfig, DecodeResult, SampleFormat, StreamInfo
from .playback import PCM16Sink, PlaybackSession, PlaybackSnapshot, PlaybackState
from .stream import StreamHandle
from .transcode import (
    BatchTranscodeItemResult,
    BatchTranscodeSummary,
    transcode_many,
    transcode_tree,
)

__all__ = [
    "PyVGMStreamError",
    "LogLevel",
    "set_log_callback",
    "disable_log_callback",
    "SampleFormat",
    "DecodeConfig",
    "StreamInfo",
    "DecodeResult",
    "BatchTranscodeItemResult",
    "BatchTranscodeSummary",
    "StreamHandle",
    "PlaybackState",
    "PlaybackSnapshot",
    "PlaybackSession",
    "PCM16Sink",
    "probe",
    "probe_buffer",
    "open_stream",
    "open_stream_from_buffer",
    "decode_to_wav_file",
    "decode_to_wav_bytes",
    "decode_buffer_to_wav_file",
    "decode_buffer_to_wav_bytes",
    "transcode_many",
    "transcode_tree",
]

__version__ = "0.1.0"
