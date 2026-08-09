"""Validate the lightweight experiment registry without PyYAML."""

from check_repo import registry_entries

VALID = {"planned", "running", "completed", "negative_result", "superseded", "archived"}
REQUIRED = {"id", "name", "track", "status", "location", "primary_question", "main_result", "reproduction_command"}


def main() -> int:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    errors: list[str] = []
    for entry in registry_entries():
        missing = REQUIRED - entry.keys()
        if missing:
            errors.append(f"{entry.get('id', '<unknown>')} missing {sorted(missing)}")
        if entry.get("status") not in VALID:
            errors.append(f"{entry.get('id')} has invalid status")
        location = root / entry.get("location", "")
        readme = location / "README.md" if location.is_dir() else location
        if not readme.exists():
            errors.append(f"{entry.get('id')} has no README/result document at {location}")
        if entry.get("status") == "completed" and entry.get("main_result", "").lower().startswith("not "):
            errors.append(f"{entry.get('id')} is completed without a documented result")
    if errors:
        print("\n".join(f"FAIL: {e}" for e in errors))
        return 1
    print(f"OK: {len(registry_entries())} experiment entries validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
