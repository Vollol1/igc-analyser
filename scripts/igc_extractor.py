#!/usr/bin/env python3
"""
igc-extractor CLI tool.

Downloads paragliding flight tracks (IGC files) from dhv-xc.de.
The tool is intentionally lightweight: plain Python + requests/BeautifulSoup,
local SQLite/JSONL storage, idempotent execution with resume support,
and credentials sourced from environment variables / .env.

See docs/decisions/ADR-001-architecture-techstack.md for architectural
principles and /home/florian/github.com/Vollol1/gag-atlas/docs/decisions/ADR-007-secrets-management.md
for secrets handling.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional


def _load_dotenv_if_available() -> None:
    """Load .env into os.environ when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv  # type: ignore

        dotenv_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(dotenv_path, override=False)
    except ImportError:
        pass


def _require_env(name: str) -> str:
    """Return an environment variable or raise a clear error."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="igc-extractor",
        description="Download IGC flight tracks from dhv-xc.de.",
    )
    parser.add_argument(
        "--flights",
        type=int,
        default=200,
        help="Number of flights to download (default: 200).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/igc"),
        help="Directory for downloaded IGC files (default: data/igc).",
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=Path("data/igc_extractor.db"),
        help="SQLite state database for resume/idempotence (default: data/igc_extractor.db).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip already downloaded flights and continue where the previous run left off.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List flights that would be downloaded without writing files.",
    )
    parser.add_argument(
        "--username",
        help="DHV-XC username (overrides DHV_XC_USERNAME from environment).",
    )
    parser.add_argument(
        "--password",
        help="DHV-XC password (overrides DHV_XC_PASSWORD from environment).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DHV_XC_BASE_URL", "https://www.dhv-xc.de"),
        help="DHV-XC base URL (default: https://www.dhv-xc.de).",
    )
    parser.add_argument(
        "--pilot-id",
        type=int,
        default=int(os.environ["DHV_XC_PILOT_ID"]) if os.environ.get("DHV_XC_PILOT_ID") else None,
        help="Optional pilot ID (overrides DHV_XC_PILOT_ID).",
    )
    return parser.parse_args(args)


def _validate_credentials(parsed: argparse.Namespace) -> tuple[str, str]:
    """Return (username, password) from CLI or environment, failing hard if absent."""
    username = parsed.username or os.environ.get("DHV_XC_USERNAME")
    password = parsed.password or os.environ.get("DHV_XC_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "DHV-XC credentials are required. Provide them via .env "
            "(DHV_XC_USERNAME / DHV_XC_PASSWORD), environment variables, "
            "or --username / --password. Never commit credentials to Git."
        )
    return username, password


def main(args: Optional[list[str]] = None) -> int:
    _load_dotenv_if_available()
    parsed = _parse_args(args)

    try:
        username, password = _validate_credentials(parsed)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Resolve paths relative to the project root (where this script lives in scripts/)
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / parsed.output_dir
    state_db = project_root / parsed.state_db

    output_dir.mkdir(parents=True, exist_ok=True)
    state_db.parent.mkdir(parents=True, exist_ok=True)

    print(f"igc-extractor configured:")
    print(f"  base_url:   {parsed.base_url}")
    print(f"  username:   {username}")
    print(f"  pilot_id:   {parsed.pilot_id}")
    print(f"  flights:    {parsed.flights}")
    print(f"  output_dir: {output_dir}")
    print(f"  state_db:   {state_db}")
    print(f"  resume:     {parsed.resume}")
    print(f"  dry_run:    {parsed.dry_run}")
    print("\nActual download implementation is pending. Use --help for options.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
