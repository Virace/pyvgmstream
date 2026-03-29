from __future__ import annotations

import argparse
import json
from pathlib import Path
from pyvgmstream import transcode_tree
from pyvgmstream.transcode import (
    DEFAULT_CHUNK_FRAMES,
    DEFAULT_DISPATCH_CHUNKSIZE,
    DEFAULT_MAX_WORKERS,
    resolve_root,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch transcode .wem files under an input root into .wav files."
    )
    parser.add_argument("input_root", help="Directory containing .wem files.")
    parser.add_argument("output_root", help="Directory to write .wav files into.")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Worker process count. Default: {DEFAULT_MAX_WORKERS}.",
    )
    parser.add_argument(
        "--chunk-frames",
        type=int,
        default=DEFAULT_CHUNK_FRAMES,
        help=f"PCM frame block size per read. Default: {DEFAULT_CHUNK_FRAMES}.",
    )
    parser.add_argument(
        "--dispatch-chunksize",
        type=int,
        default=DEFAULT_DISPATCH_CHUNKSIZE,
        help=f"Task chunksize for ProcessPoolExecutor.map. Default: {DEFAULT_DISPATCH_CHUNKSIZE}.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N .wem files discovered under the input root.",
    )
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the resolved config as JSON and exit.",
    )
    return parser


def build_config(args: argparse.Namespace) -> dict[str, object]:
    input_root = resolve_root(args.input_root)
    output_root = resolve_root(args.output_root)
    workers = max(int(args.workers), 1)
    chunk_frames = max(int(args.chunk_frames), 1)
    dispatch_chunksize = max(int(args.dispatch_chunksize), 1)
    limit = None if args.limit is None else max(int(args.limit), 0)

    return {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "workers": workers,
        "chunk_frames": chunk_frames,
        "dispatch_chunksize": dispatch_chunksize,
        "limit": limit,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = build_config(args)

    if args.print_config:
        print(json.dumps(config, ensure_ascii=False))
        return 0

    input_root = Path(config["input_root"])
    output_root = Path(config["output_root"])
    workers = int(config["workers"])
    chunk_frames = int(config["chunk_frames"])
    dispatch_chunksize = int(config["dispatch_chunksize"])
    limit = config["limit"]

    if not input_root.is_dir():
        parser.error(f"input root does not exist or is not a directory: {input_root}")

    summary = transcode_tree(
        input_root,
        output_root,
        workers=workers,
        chunk_frames=chunk_frames,
        dispatch_chunksize=dispatch_chunksize,
        limit=limit,
    )

    summary_payload = {
        "input_root": str(input_root),
        "output_root": str(output_root),
        "processed": summary.processed_count,
        "failed": summary.failed_count,
        "workers": workers,
        "chunk_frames": chunk_frames,
    }
    print(json.dumps(summary_payload, ensure_ascii=False))

    if summary.processed_count == 0:
        return 1
    if summary.failed_count:
        for result in summary.results:
            if result.error is None:
                continue
            print(
                json.dumps(
                    {"source_path": str(result.source_path), "error": result.error},
                    ensure_ascii=False,
                )
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
