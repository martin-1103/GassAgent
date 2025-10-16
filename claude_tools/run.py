#!/usr/bin/env python3
"""
Task Execution System - Python Implementation

Automated task execution that uses PhaseManager and ClaudeStreamer
to analyze, execute, validate, and manage tasks in parallel.
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
    from phase_manager import PhaseManager
except ImportError as e:
    print(f"Error importing classes: {e}")
    print(f"Make sure {class_dir} contains claude_streamer.py, worker_monitor.py, and phase_manager.py")
    sys.exit(1)


class TaskExecutionSystem:
    """Main task execution system using PhaseManager and ClaudeStreamer."""

    def __init__(self, max_tasks: int = 5):
        """
        Initialize TaskExecutionSystem

        Args:
            max_tasks: Maximum number of concurrent tasks
        """
        # Get package directory for absolute paths
        self.package_dir = Path(__file__).parent

        # Project files remain in current working directory
        self.plan_dir = Path(".ai/plan")
        self.brain_dir = Path(".ai/brain")
        self.tasks_dir = self.brain_dir / "tasks"
        self.validation_dir = self.brain_dir / "validation"
        self.status_dir = self.brain_dir / "status"

        # Template and temp files use package directory
        self.prompt_template_dir = self.package_dir / "prompt_template"
        self.prompt_tmp_dir = self.package_dir / "prompt_tmp"

        self.max_tasks = max_tasks

        # Initialize worker monitor
        self.worker_monitor = WorkerMonitor(max_workers=max_tasks)

        # Initialize managers
        self.phase_manager = PhaseManager(str(self.plan_dir))
        self.claude_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Ensure directories exist
        for dir_path in [self.prompt_tmp_dir, self.prompt_template_dir]:
            dir_path.mkdir(exist_ok=True)
        for dir_path in [self.tasks_dir, self.validation_dir, self.status_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Statistics tracking
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.start_time = None

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

    def _create_prompt_file(self, agent_name: str, context: Dict[str, Any]) -> str:
        """
        Create a prompt file for specified agent.

        Args:
            agent_name: Name of the agent
            context: Context information for the agent

        Returns:
            Path to created prompt file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = self.prompt_tmp_dir / f"{agent_name}_{timestamp}.txt"

        # Read the agent template
        agent_content = self._get_agent_template(agent_name)

        # Create focused prompt for this specific agent
        if agent_name == "task-analyzer-executor":
            available_tasks = context.get('available_tasks', [])
            tasks_json = json.dumps(available_tasks, indent=2)

            prompt = f"""You are task-analyzer-executor agent.

{agent_content}

## TASK: Analyze available tasks and create context files

**Available Tasks:**
```json
{tasks_json}
```

**Instructions:**
1. Load project context from:
   - .ai/structure/structure.md
   - .ai/schema/index.json
   - .ai/plan/phases.json
2. For each available task, create context file at: .ai/brain/tasks/[TASK_ID].md
3. Update task status to "in-progress" using PhaseManager
4. Follow all analysis and planning guidelines from the agent template
5. Return JSON with task file paths created

**Output Location:**
Save task context files to: .ai/brain/tasks/

Please proceed with task analysis now.
"""
        elif agent_name == "task-validator":
            task_id = context.get('task_id')

            prompt = f"""You are task-validator agent.

{agent_content}

## TASK: Validate task implementation quality

**Task Context:**
- Task ID: {task_id}
- Task context file: .ai/brain/tasks/{task_id}.md

**Instructions:**
1. Read task context from .ai/brain/tasks/{task_id}.md
2. Analyze implementation against requirements and scope
3. Run lint checking: pnpm run lint → pnpm run lint:fix
4. Continue until lint passes completely (0 errors, 0 warnings)
5. Check file size limits (max 300 lines) and AI-friendly naming
6. Resolve all quality issues actively
7. Create validation report at .ai/brain/validation/{task_id}_report.md
8. Return final validation status (PASS/FAIL/PARTIAL)

**Output Location:**
Save validation report to: .ai/brain/validation/{task_id}_report.md

Please proceed with task validation now.
"""
        elif agent_name == "task-status-updater":
            task_id = context.get('task_id')
            validation_result = context.get('validation_result')

            prompt = f"""You are task-status-updater agent.

{agent_content}

## TASK: Update task status based on validation results

**Task Context:**
- Task ID: {task_id}
- Validation Result: {validation_result}
- Validation Report: .ai/brain/validation/{task_id}_report.md

**Instructions:**
1. Read validation report from .ai/brain/validation/{task_id}_report.md
2. Determine status update based on validation result:
   - PASS → Update status to "completed"
   - FAIL/PARTIAL → Keep status as "in-progress"
3. Use PhaseManager.update_status() to update task status
4. Create status log at .ai/brain/status/{task_id}_log.md
5. Document reasoning for status update

**Output Location:**
Save status log to: .ai/brain/status/{task_id}_log.md

Please proceed with status management now.
"""

        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            return str(prompt_file)
        except Exception as e:
            print(f"[ERROR] Error creating prompt file: {e}")
            return ""

    def _call_agent(self, agent_name: str, context: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """
        Call agent via ClaudeStreamer with worker monitoring.

        Args:
            agent_name: Name of the agent to call
            context: Context information for the agent
            worker_id: ID of the worker processing this agent

        Returns:
            Result dictionary with success status and details
        """
        # Update worker status - starting agent
        self.worker_monitor.update_worker(worker_id, f"Starting {agent_name}", WorkerState.ACTIVE)

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
        self.total_tasks += 1
        if success:
            self.completed_tasks += 1
        else:
            self.failed_tasks += 1

    def _process_agent_worker(self, agent_name: str, context: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Worker function to process a single agent with monitoring."""
        # Call agent with worker ID for monitoring
        result = self._call_agent(agent_name, context, worker_id)

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

    def _create_task_execution_prompt(self, task_id: str) -> str:
        """Create enhanced prompt for task execution with context."""
        prompt = f"""Dengan konteks lengkap dari file .ai/brain/tasks/{task_id}.md, kerjakan task tersebut.

Project Structure: .ai/structure/structure.md
Database Schema: .ai/schema/index.json

Ikuti recommendations dan existing patterns yang sudah dianalisis.
Max 300 lines per file dengan AI-friendly naming (maksudnya submodule gitu kalau lebih dari 300 line).

Execute task sekarang."""
        return prompt

    def _execute_task(self, task: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Execute a single task using ClaudeStreamer."""
        # Update worker status - starting task execution
        self.worker_monitor.update_worker(worker_id, f"Executing task {task['id']}: {task['title']}", WorkerState.ACTIVE)

        # Create enhanced prompt with context
        prompt = self._create_task_execution_prompt(task['id'])

        # Create separate ClaudeStreamer instance for this worker
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
            self.worker_monitor.update_worker(worker_id, f"Calling Claude for task {task['id']}", WorkerState.ACTIVE)

            # Use streaming version with callback
            exit_code = worker_streamer.stream(prompt)
            response_text = ""  # Stream method doesn't return response text

            if exit_code == 0:
                self.worker_monitor.set_worker_completed(worker_id, f"Completed task {task['id']}")
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

        # Return result
        return {
            "success": success,
            "response": response_text,
            "task": task,
            "error": error_msg
        }

    def _process_task_worker(self, task: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Worker function to process a single task with monitoring."""
        # Execute the task
        result = self._execute_task(task, worker_id)

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

    def run_task_execution(self, max_tasks: int = 5):
        """
        Run the complete task execution process.

        Args:
            max_tasks: Maximum number of concurrent tasks
        """
        if not self.start_time:
            self.start_time = datetime.now()
            self.total_tasks = 0
            self.completed_tasks = 0
            self.failed_tasks = 0

        self.max_tasks = max_tasks
        print(f"Starting Task Execution System")
        print(f"Maximum concurrent tasks: {self.max_tasks}")
        print(f"Output directories: {self.brain_dir}")

        # Start worker monitoring display
        self.worker_monitor.start_display()

        try:
            # Phase 1: Task Analysis
            print(f"\n--- Phase 1: Task Analysis ---")
            print("Running task-analyzer-executor agent...")

            # Get available tasks from PhaseManager
            available_tasks = self.phase_manager.get_workable_phases()
            print(f"Found {len(available_tasks)} available tasks")

            if not available_tasks:
                print("[OK] No available tasks to execute")
                return True

            # Limit to max_tasks
            tasks_to_process = available_tasks[:self.max_tasks]
            print(f"Processing {len(tasks_to_process)} tasks (max: {self.max_tasks})")

            # Run task analyzer
            analyzer_context = {'available_tasks': tasks_to_process}
            analyzer_result = self._process_agent_worker("task-analyzer-executor", analyzer_context, 1)

            if not analyzer_result["success"]:
                print(f"[ERROR] Task analysis failed: {analyzer_result.get('error', 'Unknown error')}")
                return False

            print("[OK] Task analysis completed successfully")

            # Phase 2: Task Execution (Parallel)
            print(f"\n--- Phase 2: Task Execution ---")
            print("Executing tasks in parallel...")

            with ThreadPoolExecutor(max_workers=self.max_tasks) as executor:
                # Submit all tasks to workers
                future_to_task = {
                    executor.submit(self._process_task_worker, task, i+1): task
                    for i, task in enumerate(tasks_to_process)
                }

                # Wait for all to complete and collect results
                task_results = {}
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        task_results[task['id']] = result
                    except Exception as e:
                        self.worker_monitor.set_worker_error(1, f"Task exception: {e}")
                        self._update_statistics(False)
                        task_results[task['id']] = {"success": False, "error": str(e)}

            # Phase 3: Quality Validation (Sequential)
            print(f"\n--- Phase 3: Quality Validation ---")
            print("Running task-validator agent...")

            validation_results = {}
            for task_id, task_result in task_results.items():
                if task_result.get("success", False):
                    print(f"Validating task {task_id}...")
                    validator_context = {'task_id': task_id}
                    validator_result = self._process_agent_worker("task-validator", validator_context, 1)

                    # Extract validation status from response
                    validation_status = "FAIL"  # Default
                    if validator_result.get("success"):
                        response = validator_result.get("response", "")
                        if "PASS" in response:
                            validation_status = "PASS"
                        elif "PARTIAL" in response:
                            validation_status = "PARTIAL"

                    validation_results[task_id] = validation_status

                    if validation_status == "PASS":
                        print(f"[OK] Task {task_id} validation PASSED")
                    elif validation_status == "PARTIAL":
                        print(f"[WARNING] Task {task_id} validation PARTIAL")
                    else:
                        print(f"[ERROR] Task {task_id} validation FAILED")
                else:
                    validation_results[task_id] = "FAIL"
                    print(f"[ERROR] Task {task_id} execution failed, skipping validation")

            # Phase 4: Status Management
            print(f"\n--- Phase 4: Status Management ---")
            print("Running task-status-updater agent...")

            status_updated = 0
            for task_id, validation_result in validation_results.items():
                print(f"Updating status for task {task_id}...")
                updater_context = {
                    'task_id': task_id,
                    'validation_result': validation_result
                }
                updater_result = self._process_agent_worker("task-status-updater", updater_context, 1)

                if updater_result.get("success"):
                    status_updated += 1
                    new_status = "completed" if validation_result == "PASS" else "in-progress"
                    print(f"[OK] Task {task_id} status updated to {new_status}")
                else:
                    print(f"[ERROR] Failed to update status for task {task_id}")

            # Final summary
            print(f"\n--- Task Execution Summary ---")
            print(f"Total tasks: {self.total_tasks}")
            print(f"Completed successfully: {self.completed_tasks}")
            print(f"Failed: {self.failed_tasks}")
            print(f"Status updated: {status_updated}")

            if self.failed_tasks == 0:
                print("[OK] Task execution completed successfully!")
                return True
            else:
                print("[ERROR] Task execution completed with errors")
                return False

        except KeyboardInterrupt:
            print(f"\n\n[OK] Interrupted by user")
            print(f"Stats: {self.completed_tasks} success, {self.failed_tasks} failed")
            return False
        except Exception as e:
            print(f"\n\n[ERROR] Fatal error: {e}")
            print(f"Stats: {self.completed_tasks} success, {self.failed_tasks} failed")
            return False
        finally:
            # Stop worker monitoring display
            self.worker_monitor.stop_display()


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Task Execution System")
    parser.add_argument("--max-tasks", type=int, default=5,
                       help="Maximum number of concurrent tasks (default: 5)")

    args = parser.parse_args()

    # Initialize task execution system
    task_system = TaskExecutionSystem(max_tasks=args.max_tasks)

    # Run the task execution
    try:
        success = task_system.run_task_execution(args.max_tasks)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n[OK] Interrupted by user")
        print(f"Stats: {task_system.completed_tasks} success, {task_system.failed_tasks} failed")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        print(f"Stats: {task_system.completed_tasks} success, {task_system.failed_tasks} failed")
        sys.exit(1)


if __name__ == "__main__":
    main()