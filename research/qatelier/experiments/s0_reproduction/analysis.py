"""S0 analysis entry point, enabled only after committed raw artifacts exist."""

from __future__ import annotations

from pathlib import Path


def main(raw_directory: str = "raw") -> None:
    path = Path(raw_directory)
    if not path.exists():
        raise SystemExit(f"S0 analysis blocked: raw artifact directory does not exist: {path}")
    raise SystemExit("S0 analysis is not enabled until the preregistered runner produces raw results")


if __name__ == "__main__":
    main()
