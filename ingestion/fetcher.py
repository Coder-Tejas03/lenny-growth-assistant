"""
Lenny Growth Assistant — Transcript Acquisition Module

Downloads or discovers Lenny's Podcast transcripts from the official repository
(https://github.com/ChatPRD/lennys-podcast-transcripts) into a local cache directory.
"""

import argparse
import logging
from pathlib import Path
import subprocess
import sys
from typing import List

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts.git"
DEFAULT_CACHE_DIR = Path("data/transcripts")


class TranscriptAcquisitionError(Exception):
    """Raised when transcript download or discovery fails."""

    pass


def clone_transcript_repository(
    repo_url: str = REPO_URL,
    target_dir: Path | str = DEFAULT_CACHE_DIR,
    force: bool = False,
) -> Path:
    """
    Performs a shallow clone (--depth 1) of the transcripts repository.
    If the directory already contains transcripts and force=False, reuses existing files.
    """
    destination = Path(target_dir).resolve()

    if destination.exists() and any(destination.glob("**/*.md")) and not force:
        logger.info(f"Using existing cached transcripts in {destination}")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists() and force:
        import shutil
        shutil.rmtree(destination)

    logger.info(f"Cloning {repo_url} into {destination} (shallow clone)...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(destination)],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Successfully cloned transcript repository.")
    except subprocess.CalledProcessError as exc:
        raise TranscriptAcquisitionError(
            f"Failed to clone repository from {repo_url}: {exc.stderr}"
        ) from exc
    except FileNotFoundError as exc:
        raise TranscriptAcquisitionError(
            "Git is not installed or not in PATH."
        ) from exc

    return destination


def discover_transcript_files(source_dir: Path | str) -> List[Path]:
    """
    Finds all valid transcript markdown files within a directory.
    Ignores non-transcript documentation like README.md and CLAUDE.md.
    """
    directory = Path(source_dir).resolve()
    if not directory.is_dir():
        raise TranscriptAcquisitionError(f"Directory does not exist: {directory}")

    ignored_names = {"readme.md", "claude.md", "license.md", "contributing.md"}

    transcript_files: List[Path] = []
    for path in directory.rglob("*.md"):
        if path.name.lower() in ignored_names:
            continue
        # Skip hidden directories like .git
        if any(part.startswith(".") for part in path.parts):
            continue
        transcript_files.append(path)

    # Sort deterministically
    transcript_files.sort(key=lambda p: p.as_posix())
    return transcript_files


def main():
    """CLI runner for fetching transcripts."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="Fetch Lenny Podcast transcripts.")
    parser.add_argument(
        "--target-dir",
        type=str,
        default=str(DEFAULT_CACHE_DIR),
        help="Local directory to store transcripts",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-clone even if cache directory exists",
    )
    args = parser.parse_args()

    try:
        target = clone_transcript_repository(target_dir=args.target_dir, force=args.force)
        files = discover_transcript_files(target)
        logger.info(f"Discovered {len(files)} transcript files in {target}")
    except TranscriptAcquisitionError as exc:
        logger.error(f"Acquisition error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
