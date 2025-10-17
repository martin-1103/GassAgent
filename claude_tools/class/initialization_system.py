#!/usr/bin/env python3
"""
Initialization System

Core initialization system extracted from init.py
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..claude_streamer import ClaudeStreamer
from ..worker_monitor import WorkerMonitor, WorkerState
from ..agent_manager import AgentManager
from ..prompt_generator import PromptGenerator
from ..statistics_tracker import StatisticsTracker


class InitializationSystem:
    """Main initialization system using ClaudeStreamer for project setup."""

    def __init__(self):
        """
        Initialize InitializationSystem
        """
        # Get package directory for absolute paths
        self.package_dir = Path(__file__).parent.parent

        # Project files remain in current working directory
        self.output_base_dir = Path(".ai")
        self.plan_dir = self.output_base_dir / "plan"
        self.schema_dir = self.output_base_dir / "schema"
        self.structure_dir = self.output_base_dir / "structure"

        # Template and temp files use package directory
        self.prompt_template_dir = self.package_dir / "prompt_template"
        self.prompt_tmp_dir = self.package_dir / "prompt_tmp"

        # Initialize worker monitor
        self.worker_monitor = WorkerMonitor(max_workers=2)  # For parallel agents

        # Initialize shared components
        self.statistics_tracker = StatisticsTracker("Initialization")
        self.agent_manager = AgentManager(
            self.worker_monitor,
            self.prompt_template_dir,
            self.prompt_tmp_dir,
            self.statistics_tracker
        )
        self.prompt_generator = PromptGenerator(self.prompt_template_dir)

        # Initialize manager
        self.claude_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Ensure directories exist
        for dir_path in [self.prompt_tmp_dir, self.prompt_template_dir]:
            dir_path.mkdir(exist_ok=True)
        for dir_path in [self.plan_dir, self.schema_dir, self.structure_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def validate_inputs(self, plan_path: str, target_folder: Optional[str]) -> bool:
        """
        Validate input parameters

        Args:
            plan_path: Path to PRD/plan file
            target_folder: Target folder name (optional)

        Returns:
            True if valid, False otherwise
        """
        # Handle @ notation for file references
        if plan_path.startswith('@'):
            plan_path = plan_path[1:]

        plan_file = Path(plan_path)
        if not plan_file.exists():
            print(f"[ERROR] Plan file not found: {plan_file}")
            return False

        if not plan_file.is_file():
            print(f"[ERROR] Plan path is not a file: {plan_file}")
            return False

        # Store validated paths
        self.plan_file = plan_file
        self.target_folder = target_folder

        return True

    def _phase_1_plan_analysis(self) -> bool:
        """
        Phase 1: Sequential - Plan Analyzer

        Returns:
            True if successful, False otherwise
        """
        print("\n--- Phase 1: Plan Analysis ---")
        print("Running plan-analyzer agent...")

        try:
            # Create context for agent
            context = {
                "plan_file": str(self.plan_file),
                "target_folder": self.target_folder,
                "plan_dir": str(self.plan_dir),
                "schema_dir": str(self.schema_dir),
                "structure_dir": str(self.structure_dir)
            }

            # Generate prompt content
            agent_template = self.agent_manager.get_agent_template("plan-analyzer")
            prompt_content = self.prompt_generator.generate_plan_analyzer_prompt(
                agent_template,
                self.plan_file,
                self.target_folder,
                self.plan_dir
            )

            # Process plan analyzer agent
            plan_result = self.agent_manager.process_agent_worker(
                "plan-analyzer",
                prompt_content,
                1,
                context
            )

            if not plan_result["success"]:
                print(f"[ERROR] Plan analysis failed: {plan_result.get('error', 'Unknown error')}")
                return False

            print("[OK] Plan analysis completed successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Exception in plan analysis: {e}")
            return False

    def _phase_2_parallel_generation(self) -> bool:
        """
        Phase 2: Parallel - Database Schema Designer and Project Structure Generator

        Returns:
            True if successful, False otherwise
        """
        print("\n--- Phase 2: Parallel Generation ---")
        print("Running database-schema-designer and project-structure-generator agents...")

        parallel_agents = [
            ("database-schema-designer", "schema_designer_context"),
            ("project-structure-generator", "structure_generator_context")
        ]

        # Prepare agent contexts and prompts
        agent_tasks = []
        for agent_name, context_name in parallel_agents:
            try:
                # Create context for agent
                context = {
                    "plan_file": str(self.plan_file),
                    "target_folder": self.target_folder,
                    "plan_dir": str(self.plan_dir),
                    "schema_dir": str(self.schema_dir),
                    "structure_dir": str(self.structure_dir)
                }

                # Generate prompt content
                if agent_name == "database-schema-designer":
                    agent_template = self.agent_manager.get_agent_template(agent_name)
                    prompt_content = self.prompt_generator.generate_database_schema_designer_prompt(
                        agent_template,
                        self.plan_dir,
                        self.schema_dir,
                        self.target_folder
                    )
                elif agent_name == "project-structure-generator":
                    agent_template = self.agent_manager.get_agent_template(agent_name)
                    prompt_content = self.prompt_generator.generate_project_structure_generator_prompt(
                        agent_template,
                        self.plan_dir,
                        self.structure_dir,
                        self.target_folder
                    )

                agent_tasks.append({
                    "agent_name": agent_name,
                    "prompt_content": prompt_content,
                    "context": context
                })

            except Exception as e:
                print(f"[ERROR] Failed to prepare {agent_name}: {e}")
                return False

        # Run agents in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all agents to workers
            future_to_agent = {
                executor.submit(
                    self.agent_manager.process_agent_worker,
                    task["agent_name"],
                    task["prompt_content"],
                    i+1,
                    task["context"]
                ): task["agent_name"]
                for i, task in enumerate(agent_tasks)
            }

            # Wait for all to complete
            for future in as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                try:
                    result = future.result()
                    results[agent_name] = result
                except Exception as e:
                    self.worker_monitor.set_worker_error(1, f"Worker exception: {e}")
                    self.statistics_tracker.update_success(False)
                    results[agent_name] = {"success": False, "error": str(e)}

        # Check parallel phase results
        parallel_success = all(result.get("success", False) for result in results.values())

        if parallel_success:
            print("[OK] Parallel agents completed successfully")
        else:
            print("[ERROR] Some parallel agents failed")
            for agent_name, result in results.items():
                if not result.get("success", False):
                    print(f"  - {agent_name}: {result.get('error', 'Unknown error')}")

        return parallel_success

    def run_initialization(self, plan_path: str, target_folder: Optional[str] = None) -> bool:
        """
        Run the complete initialization process with sequential and parallel phases.

        Args:
            plan_path: Path to PRD/plan file
            target_folder: Target folder name (optional)

        Returns:
            True if successful, False otherwise
        """
        self.statistics_tracker.start_timing()

        # Validate inputs
        if not self.validate_inputs(plan_path, target_folder):
            return False

        print(f"Starting Project Initialization")
        print(f"Plan file: {self.plan_file}")
        print(f"Target folder: {self.target_folder or 'New project'}")
        print(f"Output directories: {self.output_base_dir}")

        # Start worker monitoring display
        self.worker_monitor.start_display()

        try:
            # Phase 1: Sequential - Plan Analyzer
            if not self._phase_1_plan_analysis():
                return False

            # Phase 2: Parallel - Database Schema Designer and Project Structure Generator
            if not self._phase_2_parallel_generation():
                return False

            # Final summary
            print(f"\n--- Initialization Summary ---")
            self.statistics_tracker.print_summary()

            if self.statistics_tracker.failed_items == 0:
                print("[OK] Project initialization completed successfully!")
                print(f"Generated files in: {self.output_base_dir}")
                return True
            else:
                print("[ERROR] Project initialization completed with errors")
                return False

        except KeyboardInterrupt:
            from ..shared_helpers import handle_keyboard_interrupt
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_keyboard_interrupt(stats_dict, "Initialization")
            return False
        except Exception as e:
            from ..shared_helpers import handle_fatal_error
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_fatal_error(e, stats_dict, "Initialization")
            return False
        finally:
            # Stop worker monitoring display
            self.worker_monitor.stop_display()