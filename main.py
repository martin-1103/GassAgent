#!/usr/bin/env python3
"""
Main Claude Stream CLI

Simple command-line interface using ClaudeStreamer class.
"""

import argparse
import sys
from datetime import datetime
from claude_streamer import ClaudeStreamer


def default_finish_hook():
    """Default callback called when stream finishes"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Task completed")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Stream Claude Code responses in headless mode",
        epilog="Example: %(prog)s \"Explain this code\""
    )

    parser.add_argument(
        "prompt",
        help="The prompt to send to Claude"
    )

    args = parser.parse_args()

    # Create streamer with default settings and finish hook
    streamer = ClaudeStreamer(on_finish_callback=default_finish_hook)

    # Stream response
    exit_code = streamer.stream(args.prompt)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()