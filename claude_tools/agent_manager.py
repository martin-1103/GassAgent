#!/usr/bin/env python3
"""
Agent Manager

Shared agent management and calling logic for run.py, break.py, and init.py
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .claude_streamer import ClaudeStreamer
from .worker_monitor import WorkerMonitor, WorkerState
from .statistics_tracker import StatisticsTracker


class AgentManager:
    """Shared agent management for calling Claude with different agent types"""

    def __init__(self,
                 worker_monitor: WorkerMonitor,
                 prompt_template_dir: Path,
                 prompt_tmp_dir: Path,
                 statistics_tracker: Optional[StatisticsTracker] = None):
        """
        Initialize agent manager

        Args:
            worker_monitor: WorkerMonitor instance for tracking worker status
            prompt_template_dir: Directory containing agent templates
            prompt_tmp_dir: Directory for temporary prompt files
            statistics_tracker: Optional statistics tracker
        """
        self.worker_monitor = worker_monitor
        self.prompt_template_dir = prompt_template_dir
        self.prompt_tmp_dir = prompt_tmp_dir
        self.statistics_tracker = statistics_tracker

        # Ensure directories exist
        self.prompt_template_dir.mkdir(exist_ok=True)
        self.prompt_tmp_dir.mkdir(exist_ok=True)

    def get_agent_template(self, agent_name: str) -> str:
        """
        Get the agent template content

        Args:
            agent_name: Name of the agent template

        Returns:
            Agent template content as string

        Raises:
            FileNotFoundError: If template file not found
            RuntimeError: If template file cannot be read
        """
        agent_file = self.prompt_template_dir / f"{agent_name}.md"

        if not agent_file.exists():
            raise FileNotFoundError(f"Agent template not found: {agent_file}")

        try:
            with open(agent_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Extract just the core instruction part
                if "---" in content:
                    parts = content.split("---")
                    if len(parts) > 2:
                        return "---" + "---".join(parts[1:])
            return content
        except Exception as e:
            raise RuntimeError(f"Failed to read agent template {agent_file}: {e}")

    def create_prompt_file(self,
                          agent_name: str,
                          prompt_content: str,
                          context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a prompt file for specified agent

        Args:
            agent_name: Name of the agent
            prompt_content: Base prompt content
            context: Optional context information for the agent

        Returns:
            Path to created prompt file or empty string if failed
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = self.prompt_tmp_dir / f"{agent_name}_{timestamp}.txt"

        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt_content)
            return str(prompt_file)
        except Exception as e:
            print(f"[ERROR] Error creating prompt file: {e}")
            return ""

    def create_stream_callback(self, worker_id: int) -> Callable[[str], None]:
        """
        Create a stream callback function for worker monitoring

        Args:
            worker_id: ID of the worker

        Returns:
            Callback function for streaming
        """
        def stream_callback(text: str):
            # Clean up the text and update worker status
            clean_text = text.strip().replace('\n', ' ').replace('\r', '')
            if clean_text and len(clean_text) > 0:
                # Truncate if too long
                if len(clean_text) > 40:
                    clean_text = clean_text[:37] + "..."
                self.worker_monitor.update_worker(worker_id, clean_text, WorkerState.ACTIVE)

        return stream_callback

    def call_agent(self,
                   agent_name: str,
                   prompt_content: str,
                   worker_id: int,
                   context: Optional[Dict[str, Any]] = None,
                   strategic_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call agent via ClaudeStreamer with worker monitoring

        Args:
            agent_name: Name of the agent to call
            prompt_content: Prompt content for the agent
            worker_id: ID of the worker processing this agent
            context: Optional context information
            strategic_context: Optional strategic context

        Returns:
            Result dictionary with success status and details
        """
        # Update worker status - starting agent
        self.worker_monitor.update_worker(worker_id, f"Starting {agent_name}", WorkerState.ACTIVE)

        # Create prompt file
        prompt_file = self.create_prompt_file(agent_name, prompt_content, context)
        if not prompt_file:
            self.worker_monitor.set_worker_error(worker_id, "Failed to create prompt file")
            return {
                "success": False,
                "error": "Failed to create prompt file",
                "agent_name": agent_name
            }

        # Create separate ClaudeStreamer instance for each worker to avoid callback conflicts
        worker_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Define stream callback for worker monitoring
        stream_callback = self.create_stream_callback(worker_id)

        try:
            # Update worker status - calling Claude
            self.worker_monitor.update_worker(worker_id, f"Calling Claude for {agent_name}", WorkerState.ACTIVE)

            # Use streaming version with callback (separate streamer instance)
            response_text, exit_code = worker_streamer.get_response_from_file_with_stream(
                prompt_file, stream_callback
            )

            if exit_code == 0:
                self.worker_monitor.set_worker_completed(worker_id, f"Completed {agent_name}")
                success = True
                error_msg = None
            else:
                self.worker_monitor.set_worker_error(worker_id, f"Claude error (exit code: {exit_code})")
                error_msg = f"Claude returned exit code {exit_code}"
                success = False

        except Exception as e:
            self.worker_monitor.set_worker_error(worker_id, f"Exception: {str(e)}")
            error_msg = f"Exception: {e}"
            success = False

        finally:
            # Clean up prompt file
            try:
                os.remove(prompt_file)
            except Exception:
                pass

        # Update statistics if tracker is available
        if self.statistics_tracker:
            self.statistics_tracker.update_success(success)

        # Return result
        result = {
            "success": success,
            "response": response_text,
            "agent_name": agent_name,
            "error": error_msg,
            "prompt_file": prompt_file
        }

        # Add context to result if provided
        if strategic_context:
            result["strategic_context"] = strategic_context

        return result

    def process_agent_worker(self,
                             agent_name: str,
                             prompt_content: str,
                             worker_id: int,
                             context: Optional[Dict[str, Any]] = None,
                             strategic_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Worker function to process a single agent with monitoring

        Args:
            agent_name: Name of the agent to process
            prompt_content: Prompt content for the agent
            worker_id: ID of the worker
            context: Optional context information
            strategic_context: Optional strategic context

        Returns:
            Result from agent call
        """
        # Call agent with worker ID for monitoring
        result = self.call_agent(agent_name, prompt_content, worker_id, context, strategic_context)

        # Set worker back to idle when done
        if result["success"]:
            self.worker_monitor.set_worker_idle(worker_id)
        else:
            # Keep error state visible for a moment, then set to idle
            import threading
            import time

            def delayed_idle():
                time.sleep(2)  # Show error for 2 seconds
                self.worker_monitor.set_worker_idle(worker_id)

            threading.Thread(target=delayed_idle, daemon=True).start()

        return result

    def get_agent_list(self) -> list[str]:
        """
        Get list of available agent templates

        Returns:
            List of agent names (without .md extension)
        """
        agents = []
        if self.prompt_template_dir.exists():
            for file_path in self.prompt_template_dir.glob("*.md"):
                agents.append(file_path.stem)
        return sorted(agents)

    def validate_agent_exists(self, agent_name: str) -> bool:
        """
        Check if agent template exists

        Args:
            agent_name: Name of the agent to check

        Returns:
            True if agent template exists, False otherwise
        """
        agent_file = self.prompt_template_dir / f"{agent_name}.md"
        return agent_file.exists()

    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """
        Get information about an agent template

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with agent information
        """
        agent_file = self.prompt_template_dir / f"{agent_name}.md"
        info = {
            "name": agent_name,
            "exists": False,
            "path": str(agent_file),
            "size": 0,
            "modified": None
        }

        if agent_file.exists():
            info["exists"] = True
            info["size"] = agent_file.stat().st_size
            info["modified"] = datetime.fromtimestamp(agent_file.stat().st_mtime)

        return info