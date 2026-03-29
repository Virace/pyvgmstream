from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

DEFAULT_VOLUME_PERCENT = 10.0


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


def play(source_path: Path, volume_percent: float, max_seconds: float | None) -> None:
    from pyvgmstream.playback import PlaybackState
    from pyvgmstream.playback.backends.sounddevice import create_sounddevice_session

    session = create_sounddevice_session(source_path, volume_percent=volume_percent)
    session.start()

    try:
        if max_seconds is None:
            session.wait()
        else:
            while True:
                snapshot = session.snapshot()
                if snapshot.state in {PlaybackState.FINISHED, PlaybackState.STOPPED, PlaybackState.ERROR}:
                    break
                if snapshot.position_seconds >= max_seconds:
                    session.stop()
                    break
                time.sleep(0.01)
    finally:
        if session.snapshot().state not in {PlaybackState.FINISHED, PlaybackState.STOPPED, PlaybackState.ERROR}:
            session.stop()

    snapshot = session.snapshot()
    if snapshot.state is PlaybackState.ERROR:
        raise RuntimeError(snapshot.recent_error or "playback failed")


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
