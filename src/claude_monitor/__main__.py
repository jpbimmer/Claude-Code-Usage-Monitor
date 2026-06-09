"""Entry point: claude-monitor / ccm"""

import argparse
import logging

from claude_monitor import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="claude-monitor",
        description="Live Claude Pro usage dashboard",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--data-path", default=None, metavar="PATH",
        help="Path to ~/.claude/projects (default: auto-detected)",
    )
    parser.add_argument(
        "--refresh", type=float, default=1.0, metavar="SECONDS",
        help="Display refresh interval in seconds (default: 1.0)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    from claude_monitor.cli import run
    run(data_path=args.data_path, refresh_rate=args.refresh)


if __name__ == "__main__":
    main()
