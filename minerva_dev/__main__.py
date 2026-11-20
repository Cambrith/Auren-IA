"""Permite executar `python -m minerva_dev`."""

import sys

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
