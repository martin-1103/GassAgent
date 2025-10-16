#!/usr/bin/env python3
"""
Project Initialization System - Python Implementation

Automated project initialization that uses ClaudeStreamer
to analyze PRD and generate development phases, database schema, and project structure.
"""

import os
import json
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# Import our classes
current_dir = os.path.dirname(os.path.abspath(__file__))
class_dir = os.path.join(current_dir, 'class')
if class_dir not in sys.path:
    sys.path.insert(0, class_dir)

try:
    from claude_streamer import ClaudeStreamer
    from worker_monitor import WorkerMonitor, WorkerState
except ImportError as e:
    print(f"Error importing classes: {e}")
    print(f"Make sure {class_dir} contains claude_streamer.py and worker_monitor.py")
    sys.exit(1)


class InitializationSystem:
    """Main initialization system using ClaudeStreamer for project setup."""

    def __init__(self):
        """
        Initialize InitializationSystem
        """
        # Get package directory for absolute paths
        self.package_dir = Path(__file__).parent

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

        # Statistics tracking
        self.total_agents = 0
        self.successful_agents = 0
        self.failed_agents = 0
        self.start_time = None

    def _validate_inputs(self, plan_path: str, target_folder: Optional[str]) -> bool:
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

    def _create_prompt_file(self, agent_name: str, context: Dict[str, Any]) -> str:
        """
        Create a prompt file for specified agent.

        Args:
            agent_name: Name of the agent (plan-analyzer, database-schema-designer, project-structure-generator)
            context: Context information for the agent

        Returns:
            Path to created prompt file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = self.prompt_tmp_dir / f"{agent_name}_{timestamp}.txt"

        # Read the agent template
        agent_content = self._get_agent_template(agent_name)

        # Create focused prompt for this specific agent
        if agent_name == "plan-analyzer":
            prompt = f"""You are plan-analyzer agent.

{agent_content}

## TASK: Analyze PRD and generate development phases

**Input Information:**
- Plan File: {self.plan_file}
- Target Folder: {self.target_folder or 'Not specified'}

**Instructions:**
1. Read and analyze the plan file: {self.plan_file}
2. {f'Analyze existing project in: {self.target_folder}' if self.target_folder else 'Treat as new project'}
3. Generate comprehensive development phases with dependencies
4. Create index.json and phases.json in {self.plan_dir}
5. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {self.plan_dir}/

Please proceed with the analysis now.
"""
        elif agent_name == "database-schema-designer":
            prompt = f"""You are database-schema-designer agent.

{agent_content}

## TASK: Generate phase-aware database schema

**Input Context:**
- Plan analysis available in: {self.plan_dir}/
- Target Folder: {self.target_folder or 'Not specified'}

**Instructions:**
1. Read plan analysis from {self.plan_dir}/index.json and {self.plan_dir}/phases.json
2. Analyze data requirements based on development phases
3. Design phase-aware database schema
4. Generate schema files in {self.schema_dir}/
5. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {self.schema_dir}/

Please proceed with the database schema design now.
"""
        elif agent_name == "project-structure-generator":
            prompt = f"""You are project-structure-generator agent.

{agent_content}

## TASK: Generate phase-aware project structure

**Input Context:**
- Plan analysis available in: {self.plan_dir}/
- Target Folder: {self.target_folder or 'project'}

**Instructions:**
1. Read plan analysis from {self.plan_dir}/index.json and {self.plan_dir}/phases.json
2. {f'Scan existing project structure in: {self.target_folder}' if self.target_folder else 'Design new project structure'}
3. Design phase-aware directory structure
4. Use "{self.target_folder or 'project'}" as root directory name
5. Generate structure.md in {self.structure_dir}/
6. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {self.structure_dir}/structure.md

Please proceed with the project structure generation now.
"""

        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            return str(prompt_file)
        except Exception as e:
            print(f"[ERROR] Error creating prompt file: {e}")
            return ""

    def _get_agent_template(self, agent_name: str) -> str:
        """Get the agent template content."""
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

    def _call_agent(self, agent_name: str, worker_id: int) -> Dict[str, Any]:
        """
        Call agent via ClaudeStreamer with worker monitoring.

        Args:
            agent_name: Name of the agent to call
            worker_id: ID of the worker processing this agent

        Returns:
            Result dictionary with success status and details
        """
        # Update worker status - starting agent
        self.worker_monitor.update_worker(worker_id, f"Starting {agent_name}", WorkerState.ACTIVE)

        # Create context for agent
        context = {
            "plan_file": str(self.plan_file),
            "target_folder": self.target_folder,
            "plan_dir": str(self.plan_dir),
            "schema_dir": str(self.schema_dir),
            "structure_dir": str(self.structure_dir)
        }

        # Create prompt file
        prompt_file = self._create_prompt_file(agent_name, context)
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
        def stream_callback(text: str):
            # Clean up the text and update worker status
            clean_text = text.strip().replace('\n', ' ').replace('\r', '')
            if clean_text and len(clean_text) > 0:
                # Truncate if too long
                if len(clean_text) > 40:
                    clean_text = clean_text[:37] + "..."
                self.worker_monitor.update_worker(worker_id, clean_text, WorkerState.ACTIVE)

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

        # Return result
        return {
            "success": success,
            "response": response_text,
            "agent_name": agent_name,
            "error": error_msg,
            "prompt_file": prompt_file
        }

    def _update_statistics(self, success: bool):
        """Update processing statistics."""
        self.total_agents += 1
        if success:
            self.successful_agents += 1
        else:
            self.failed_agents += 1

    def _process_agent_worker(self, agent_name: str, worker_id: int) -> Dict[str, Any]:
        """Worker function to process a single agent with monitoring."""
        # Call agent with worker ID for monitoring
        result = self._call_agent(agent_name, worker_id)

        # Update statistics
        self._update_statistics(result["success"])

        # Set worker back to idle when done
        if result["success"]:
            self.worker_monitor.set_worker_idle(worker_id)
        else:
            # Keep error state visible for a moment, then set to idle
            import threading
            def delayed_idle():
                import time
                time.sleep(2)  # Show error for 2 seconds
                self.worker_monitor.set_worker_idle(worker_id)
            threading.Thread(target=delayed_idle, daemon=True).start()

        return result

    def run_initialization(self, plan_path: str, target_folder: Optional[str] = None):
        """
        Run the complete initialization process with sequential and parallel phases.

        Args:
            plan_path: Path to PRD/plan file
            target_folder: Target folder name (optional)
        """
        if not self.start_time:
            self.start_time = datetime.now()
            self.total_agents = 0
            self.successful_agents = 0
            self.failed_agents = 0

        # Validate inputs
        if not self._validate_inputs(plan_path, target_folder):
            return False

        print(f"Starting Project Initialization")
        print(f"Plan file: {self.plan_file}")
        print(f"Target folder: {self.target_folder or 'New project'}")
        print(f"Output directories: {self.output_base_dir}")

        # Start worker monitoring display
        self.worker_monitor.start_display()

        try:
            # Phase 1: Sequential - Plan Analyzer
            print(f"\n--- Phase 1: Plan Analysis ---")
            print("Running plan-analyzer agent...")

            plan_result = self._process_agent_worker("plan-analyzer", 1)

            if not plan_result["success"]:
                print(f"[ERROR] Plan analysis failed: {plan_result.get('error', 'Unknown error')}")
                return False

            print("[OK] Plan analysis completed successfully")

            # Phase 2: Parallel - Database Schema Designer and Project Structure Generator
            print(f"\n--- Phase 2: Parallel Generation ---")
            print("Running database-schema-designer and project-structure-generator agents...")

            parallel_agents = ["database-schema-designer", "project-structure-generator"]

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit all agents to workers
                future_to_agent = {
                    executor.submit(self._process_agent_worker, agent, i+1): agent
                    for i, agent in enumerate(parallel_agents)
                }

                # Wait for all to complete
                results = {}
                for future in as_completed(future_to_agent):
                    agent = future_to_agent[future]
                    try:
                        result = future.result()
                        results[agent] = result
                    except Exception as e:
                        self.worker_monitor.set_worker_error(1, f"Worker exception: {e}")
                        self._update_statistics(False)
                        results[agent] = {"success": False, "error": str(e)}

            # Check parallel phase results
            parallel_success = all(result.get("success", False) for result in results.values())

            if parallel_success:
                print("[OK] Parallel agents completed successfully")
            else:
                print("[ERROR] Some parallel agents failed")
                for agent, result in results.items():
                    if not result.get("success", False):
                        print(f"  - {agent}: {result.get('error', 'Unknown error')}")

            # Final summary
            print(f"\n--- Initialization Summary ---")
            print(f"Total agents: {self.total_agents}")
            print(f"Successful: {self.successful_agents}")
            print(f"Failed: {self.failed_agents}")

            if self.failed_agents == 0:
                print("[OK] Project initialization completed successfully!")
                print(f"Generated files in: {self.output_base_dir}")
                return True
            else:
                print("[ERROR] Project initialization completed with errors")
                return False

        except KeyboardInterrupt:
            print(f"\n\n[OK] Interrupted by user")
            print(f"Stats: {self.successful_agents} success, {self.failed_agents} failed")
            return False
        except Exception as e:
            print(f"\n\n[ERROR] Fatal error: {e}")
            print(f"Stats: {self.successful_agents} success, {self.failed_agents} failed")
            return False
        finally:
            # Stop worker monitoring display
            self.worker_monitor.stop_display()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Project Initialization System")
    parser.add_argument("plan_path", help="Path to PRD/plan file (supports @ notation)")
    parser.add_argument("target_folder", nargs='?', help="Target folder name (optional)")

    args = parser.parse_args()

    # Initialize system
    init_system = InitializationSystem()

    # Run the initialization
    try:
        success = init_system.run_initialization(args.plan_path, args.target_folder)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n[OK] Interrupted by user")
        print(f"Stats: {init_system.successful_agents} success, {init_system.failed_agents} failed")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        print(f"Stats: {init_system.successful_agents} success, {init_system.failed_agents} failed")
        sys.exit(1)


if __name__ == "__main__":
    main()