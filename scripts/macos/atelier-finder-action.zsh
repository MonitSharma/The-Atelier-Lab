#!/bin/zsh
# Quick Action entrypoint. Automator passes the selected file as $1.
# The script deliberately calls the local backend/CLI and never installs a
# watcher or sends the selected file to a cloud provider.

set -euo pipefail

if [[ $# -lt 1 || ! -e "$1" ]]; then
  print -u2 "Atelier Quick Action requires one selected file or folder."
  exit 2
fi

ACTION="${ATELIER_FINDER_ACTION:-send_to_atelier}"
exec atelier finder execute "$ACTION" "$1"
