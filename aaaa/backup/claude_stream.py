#!/usr/bin/env python3
"""
Claude Code Streaming CLI

A simple Python CLI tool for streaming Claude Code responses in headless mode.
"""

import subprocess
import json
import sys
import argparse
import platform


def stream_claude_response(prompt: str) -> int:
    """
    Stream Claude Code response to stdout

    Args:
        prompt: The prompt to send to Claude

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Determine the correct claude command for the platform
    claude_cmd = "claude.cmd" if platform.system() == "Windows" else "claude"

    # Build command with default settings for automation
    cmd = [
        claude_cmd, "-p", prompt,
        "--output-format", "stream-json",
        "--permission-mode", "acceptEdits",
        "--verbose"
    ]

    try:
        # Start subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )

        # Stream stdout
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                try:
                    data = json.loads(line)
                    msg_type = data.get('type')

                    if msg_type == 'assistant':
                        # Extract and print text content
                        message = data.get('message', {})
                        content_parts = message.get('content', [])

                        for part in content_parts:
                            if part.get('type') == 'text':
                                text_content = part.get('text', '')
                                print(text_content, end='', flush=True)

                    elif msg_type == 'result':
                        # Show completion message
                        print("\n[FINISHED]", flush=True)

                except json.JSONDecodeError:
                    # If not valid JSON, print as-is
                    print(line, end='', flush=True)

        # Wait for process to complete
        process.wait()

        # Handle errors
        stderr_output = process.stderr.read()
        if stderr_output:
            print(f"\nError: {stderr_output}", file=sys.stderr)

        return process.returncode

    except FileNotFoundError:
        print("Error: 'claude' command not found. Please install Claude Code CLI.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


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
    exit_code = stream_claude_response(args.prompt)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()