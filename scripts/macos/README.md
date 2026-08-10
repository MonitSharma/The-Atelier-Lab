# Atelier macOS actions

`atelier-finder-action.zsh` is the shared entrypoint for four user-invoked
Finder/Shortcuts actions:

- `send_to_atelier`
- `add_to_library`
- `characterize_paper`
- `explain_file`

To create an Automator Quick Action, open Automator → New → Quick Action,
choose “files or folders” in Finder, add “Run Shell Script,” pass input as
arguments, and select this script. Set `ATELIER_FINDER_ACTION` in the action's
environment to the desired action. The action calls the local Atelier backend
through the installed `atelier` command and remains opt-in; no watcher or
whole-disk indexing is installed.

Shortcuts can use “Run Shell Script” with the same script and pass the selected
file path as the first argument. The active Atelier workspace still controls
read/write/privacy permissions.
