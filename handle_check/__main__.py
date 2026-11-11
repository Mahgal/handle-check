"""handle-check CLI entry point: ``python -m handle_check``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
