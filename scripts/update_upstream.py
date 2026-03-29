from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_REPOSITORY = "https://github.com/vgmstream/vgmstream.git"
DEFAULT_TARGET = Path("vendor") / "vgmstream"
DEFAULT_WORKTREE = Path(".temp") / "upstream-sync" / "vgmstream"


def resolve_target(raw_target: str | None = None) -> Path:
    candidate = Path(raw_target) if raw_target else DEFAULT_TARGET
    return candidate.resolve()


def resolve_worktree(raw_worktree: str | None = None) -> Path:
    candidate = Path(raw_worktree) if raw_worktree else DEFAULT_WORKTREE
    return candidate.resolve()


def run_git(args: list[str], cwd: Path | None = None, dry_run: bool = False) -> int:
    command = ["git", *args]
    if dry_run:
        print(" ".join(command))
        return 0

    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def mirror_checkout(source: Path, target: Path, dry_run: bool) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print(f"mirror {source} -> {target}")
        return 0

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git"),
    )
    return 0


def clone_or_update(target: Path, repository: str, branch: str, worktree: Path, dry_run: bool) -> int:
    worktree.parent.mkdir(parents=True, exist_ok=True)

    if not worktree.exists():
        clone_code = run_git(
            ["clone", "--branch", branch, "--single-branch", repository, str(worktree)],
            dry_run=dry_run,
        )
        if clone_code != 0:
            return clone_code
        return mirror_checkout(worktree, target, dry_run=dry_run)

    if not worktree.joinpath(".git").exists():
        raise RuntimeError(f"Worktree exists but is not a git checkout: {worktree}")

    fetch_code = run_git(["fetch", "origin", branch], cwd=worktree, dry_run=dry_run)
    if fetch_code != 0:
        return fetch_code

    pull_code = run_git(["pull", "--ff-only", "origin", branch], cwd=worktree, dry_run=dry_run)
    if pull_code != 0:
        return pull_code

    return mirror_checkout(worktree, target, dry_run=dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clone or update the local vgmstream checkout used for pyvgmstream development."
    )
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--branch", default="master")
    parser.add_argument("--target")
    parser.add_argument("--worktree")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-target", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    target = resolve_target(args.target)
    worktree = resolve_worktree(args.worktree)
    if args.print_target:
        print(target)
        return 0

    return clone_or_update(
        target=target,
        repository=args.repository,
        branch=args.branch,
        worktree=worktree,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
