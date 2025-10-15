#!/usr/bin/env python3
"""
Claude Code Streamer Class

A reusable class for streaming Claude Code responses in headless mode.
"""

import subprocess
import json
import sys
import platform
from typing import Optional, Callable


class ClaudeStreamer:
    """A class for streaming Claude Code responses in headless mode."""

    def __init__(self,
                 permission_mode: str = "acceptEdits",
                 output_format: str = "stream-json",
                 verbose: bool = True,
                 on_finish_callback: Optional[Callable] = None):
        """
        Initialize Claude Streamer

        Args:
            permission_mode: Permission mode for Claude CLI
            output_format: Output format for Claude CLI
            verbose: Enable verbose logging
            on_finish_callback: Function to call when stream finishes
        """
        self.permission_mode = permission_mode
        self.output_format = output_format
        self.verbose = verbose
        self.on_finish_callback = on_finish_callback
        self.finish_hook_called = False
        self.claude_cmd = "claude.cmd" if platform.system() == "Windows" else "claude"

    def _build_command(self, prompt: str, extra_args: Optional[list] = None) -> list:
        """Build the Claude CLI command."""
        cmd = [
            self.claude_cmd, "-p", prompt,
            "--output-format", self.output_format,
            "--permission-mode", self.permission_mode
        ]

        if self.verbose:
            cmd.append("--verbose")

        if extra_args:
            cmd.extend(extra_args)

        return cmd

    def _process_stream_line(self, line: str) -> bool:
        """
        Process a single line from the stream.

        Returns:
            bool: True if processing should continue, False if finished
        """
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
                return False

        except json.JSONDecodeError:
            # If not valid JSON, print as-is
            print(line, end='', flush=True)

        return True

    def stream(self, prompt: str, extra_args: Optional[list] = None) -> int:
        """
        Stream Claude Code response to stdout

        Args:
            prompt: The prompt to send to Claude
            extra_args: Additional CLI arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        cmd = self._build_command(prompt, extra_args)

        try:
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
                    should_continue = self._process_stream_line(line)
                    if not should_continue:
                        break

            # Wait for process to complete
            process.wait()

            # Call finish hook if provided and not already called
            if self.on_finish_callback and not self.finish_hook_called:
                try:
                    self.on_finish_callback()
                    self.finish_hook_called = True
                except:
                    pass  # Ignore errors in callback

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

    def get_response(self, prompt: str, extra_args: Optional[list] = None) -> tuple:
        """
        Get Claude response without streaming (capture output)

        Args:
            prompt: The prompt to send to Claude
            extra_args: Additional CLI arguments

        Returns:
            tuple: (response_text, exit_code)
        """
        # Override output format for capturing
        temp_format = self.output_format
        self.output_format = "json"

        try:
            cmd = self._build_command(prompt, extra_args)

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if process.returncode == 0:
                try:
                    data = json.loads(process.stdout)
                    if isinstance(data, dict):
                        response_text = data.get('result', '')
                    elif isinstance(data, list):
                        # Handle stream-json format (array of messages)
                        response_text = ""
                        for item in data:
                            if isinstance(item, dict) and item.get('type') == 'result':
                                response_text = item.get('result', '')
                                break
                        else:
                            # If no result found, try to extract text from assistant messages
                            for item in data:
                                if isinstance(item, dict) and item.get('type') == 'assistant':
                                    message = item.get('message', {})
                                    content_parts = message.get('content', [])
                                    for part in content_parts:
                                        if part.get('type') == 'text':
                                            response_text = part.get('text', '')
                                            if response_text:
                                                break
                                    if response_text:
                                        break
                    else:
                        response_text = process.stdout
                except json.JSONDecodeError:
                    response_text = process.stdout
            else:
                response_text = ""

            return response_text, process.returncode

        finally:
            # Restore original format
            self.output_format = temp_format