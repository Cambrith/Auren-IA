#!/usr/bin/env bash
set -euo pipefail
lunvri_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$lunvri_root/../cavren-nextchat/.venv/bin/python" "$lunvri_root/scripts/lunvri_desktop.py" "$@"
