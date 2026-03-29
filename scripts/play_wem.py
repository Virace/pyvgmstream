from __future__ import annotations

import argparse
from array import array
import json
from pathlib import Path

from pyvgmstream import open_stream


DEFAULT_VOLUME_PERCENT = 10.0
DEFAULT_BLOCK_FRAMES = 4096


def default_sample_path() -> Path:
    wem_dir = Path(".temp") / "wem"
    sample = next(iter(sorted(wem_dir.glob("*.wem"))), None)
    if sample is None:
        raise FileNotFoundError("no .wem sample found under .temp/wem")
    return sample.resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Play a WEM file through the local audio device.")
    parser.add_argument("source", nargs="?", help="Path to a .wem file. Defaults to the first file under .temp/wem.")
    parser.add_argument("--volume", type=float, default=DEFAULT_VOLUME_PERCENT, help="Playback volume in percent. Default: 10.")
    parser.add_argument("--max-seconds", type=float, default=None, help="Stop after N seconds of decoded audio.")
    parser.add_argument("--print-config", action="store_true", help="Print the resolved playback config as JSON and exit.")
    return parser


def resolve_source(source: str | None) -> Path:
    return Path(source).expanduser().resolve() if source else default_sample_path()


def scale_pcm16(chunk: bytes, volume_percent: float) -> bytes:
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


def play(source_path: Path, volume_percent: float, max_seconds: float | None) -> None:
    import sounddevice as sd

    with open_stream(source_path) as stream:
        with sd.RawOutputStream(
            samplerate=stream.sample_rate,
            channels=stream.channels,
            dtype="int16",
        ) as output_stream:
            while not stream.done:
                chunk = stream.read_pcm16(DEFAULT_BLOCK_FRAMES)
                if chunk:
                    output_stream.write(scale_pcm16(chunk, volume_percent))
                if max_seconds is not None and stream.tell_seconds() >= max_seconds:
                    break


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = resolve_source(args.source)
    payload = {
        "source_path": str(source_path),
        "volume_percent": float(args.volume),
        "max_seconds": args.max_seconds,
    }
    if args.print_config:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    play(source_path=source_path, volume_percent=float(args.volume), max_seconds=args.max_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
