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
                 on_finish_callback: Optional[Callable] = None,
                 stream_callback: Optional[Callable[[str], None]] = None):
        """
        Initialize Claude Streamer

        Args:
            permission_mode: Permission mode for Claude CLI
            output_format: Output format for Claude CLI
            verbose: Enable verbose logging
            on_finish_callback: Function to call when stream finishes
            stream_callback: Function to call for each stream line (worker monitoring)
        """
        self.permission_mode = permission_mode
        self.output_format = output_format
        self.verbose = verbose
        self.on_finish_callback = on_finish_callback
        self.stream_callback = stream_callback
        self.finish_hook_called = False
        self.claude_cmd = "claude.cmd" if platform.system() == "Windows" else "claude"

    def _build_command(self, prompt: str, extra_args: Optional[list] = None) -> list:
        """Build the Claude CLI command."""
        cmd = [
            self.claude_cmd, "-p",
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

                        # Call stream callback if provided (for worker monitoring)
                        if self.stream_callback:
                            self.stream_callback(text_content)

                        # Print to stdout if not in worker mode
                        if not self.stream_callback:
                            print(text_content, end='', flush=True)

            elif msg_type == 'result':
                # Show completion message
                if not self.stream_callback:
                    print("\n[FINISHED]", flush=True)
                return False

        except json.JSONDecodeError:
            # If not valid JSON, print as-is
            if self.stream_callback:
                self.stream_callback(line)
            else:
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
                encoding='utf-8',
                errors='replace',
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
            cmd, prompt_content = self._build_command(prompt, extra_args)

            # Debug output (safe ASCII)
            print(f"[DEBUG] Claude command: {' '.join(cmd)}")
            print(f"[DEBUG] Prompt length: {len(prompt_content)} chars")
            print(f"[DEBUG] First 100 chars: {prompt_content[:100].encode('ascii', errors='ignore').decode('ascii')}")

            # Use stdin for long prompts
            process = subprocess.run(
                cmd,
                input=prompt_content,  # Send via stdin instead of command line
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Debug output (safe ASCII)
            print(f"[DEBUG] Return code: {process.returncode}")
            print(f"[DEBUG] Stdout length: {len(process.stdout)} chars")
            print(f"[DEBUG] Stderr length: {len(process.stderr)} chars")
            print(f"[DEBUG] Stderr content: '{process.stderr}'")
            if process.stdout:
                print(f"[DEBUG] Stdout preview: {process.stdout[:100].encode('ascii', errors='ignore').decode('ascii')}")

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

    def get_response_from_file_with_stream(self, file_path: str, stream_callback: Callable[[str], None], extra_args: Optional[list] = None) -> tuple:
        """
        Get Claude response from file with streaming callback for worker monitoring

        Args:
            file_path: Path to file containing prompt
            stream_callback: Function to call for each stream line
            extra_args: Additional CLI arguments

        Returns:
            tuple: (response_text, exit_code)
        """
        # Override output format for streaming
        temp_format = self.output_format
        self.output_format = "stream-json"

        try:
            cmd = self._build_command("", extra_args)

            # Use @file syntax instead of reading file content
            file_prompt = f"@{file_path}"
            cmd[1] = file_prompt  # Replace "-p" with "@filename"

            # Set stream callback
            self.stream_callback = stream_callback

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1  # Line buffered
            )

            # Stream stdout and capture response
            response_parts = []
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    should_continue = self._process_stream_line(line)
                    if not should_continue:
                        break
                    # Capture response text
                    response_parts.append(line)

            # Wait for process to complete
            process.wait()

            # Handle errors
            stderr_output = process.stderr.read()
            if stderr_output:
                stream_callback(f"[ERROR] {stderr_output}")

            # Combine response
            response_text = ''.join(response_parts)

            return response_text, process.returncode

        except Exception as e:
            stream_callback(f"[ERROR] Exception: {e}")
            return "", 1

        finally:
            # Restore original format and callback
            self.output_format = temp_format
            self.stream_callback = None

    def get_response_from_file(self, file_path: str, extra_args: Optional[list] = None) -> tuple:
        """
        Get Claude response from file using @file syntax

        Args:
            file_path: Path to file containing prompt
            extra_args: Additional CLI arguments

        Returns:
            tuple: (response_text, exit_code)
        """
        # Override output format for capturing
        temp_format = self.output_format
        self.output_format = "json"

        try:
            cmd = self._build_command("", extra_args)

            # Use @file syntax instead of reading file content
            file_prompt = f"@{file_path}"
            cmd[1] = file_prompt  # Replace "-p" with "@filename"

            # Debug output (safe ASCII)
            print(f"[DEBUG] Claude command: {' '.join(cmd)}")
            print(f"[DEBUG] File path: {file_path}")

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Debug output (safe ASCII)
            print(f"[DEBUG] Return code: {process.returncode}")
            print(f"[DEBUG] Stdout length: {len(process.stdout)} chars")
            print(f"[DEBUG] Stderr length: {len(process.stderr)} chars")
            print(f"[DEBUG] Stderr content: '{process.stderr}'")
            if process.stdout:
                print(f"[DEBUG] Stdout preview: {process.stdout[:100].encode('ascii', errors='ignore').decode('ascii')}")

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

    def get_response_from_file_with_stream(self, file_path: str, stream_callback: Callable[[str], None], extra_args: Optional[list] = None) -> tuple:
        """
        Get Claude response from file with streaming callback for worker monitoring

        Args:
            file_path: Path to file containing prompt
            stream_callback: Function to call for each stream line
            extra_args: Additional CLI arguments

        Returns:
            tuple: (response_text, exit_code)
        """
        # Override output format for streaming
        temp_format = self.output_format
        self.output_format = "stream-json"

        try:
            cmd = self._build_command("", extra_args)

            # Use @file syntax instead of reading file content
            file_prompt = f"@{file_path}"
            cmd[1] = file_prompt  # Replace "-p" with "@filename"

            # Set stream callback
            self.stream_callback = stream_callback

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1  # Line buffered
            )

            # Stream stdout and capture response
            response_parts = []
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    should_continue = self._process_stream_line(line)
                    if not should_continue:
                        break
                    # Capture response text
                    response_parts.append(line)

            # Wait for process to complete
            process.wait()

            # Handle errors
            stderr_output = process.stderr.read()
            if stderr_output:
                stream_callback(f"[ERROR] {stderr_output}")

            # Combine response
            response_text = ''.join(response_parts)

            return response_text, process.returncode

        except Exception as e:
            stream_callback(f"[ERROR] Exception: {e}")
            return "", 1

        finally:
            # Restore original format and callback
            self.output_format = temp_format
            self.stream_callback = None