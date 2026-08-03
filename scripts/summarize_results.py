"""Render a registry-grounded Markdown results index."""

from check_repo import registry_entries


def main() -> int:
    print("# Registered experiment results\n")
    print("| ID | Track | Status | Main result |\n|---|---|---|---|")
    for item in registry_entries():
        print(f"| {item.get('id')} | {item.get('track')} | {item.get('status')} | {item.get('main_result')} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
