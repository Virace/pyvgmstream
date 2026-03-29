"""`pyvgmstream` 的公开 Python 包入口。"""

from .api import decode_to_wav_bytes, decode_to_wav_file, open_stream, probe
from .errors import PyVGMStreamError
from .models import DecodeResult, StreamInfo
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
    "open_stream",
    "decode_to_wav_file",
    "decode_to_wav_bytes",
    "transcode_many",
    "transcode_tree",
]

__version__ = "0.1.0"
