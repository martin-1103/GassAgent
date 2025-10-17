#!/usr/bin/env python3
"""
Task Execution System

Core task execution system extracted from run.py
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..claude_streamer import ClaudeStreamer
from ..worker_monitor import WorkerMonitor, WorkerState
from .phase_manager import PhaseManager
from ..agent_manager import AgentManager
from ..prompt_generator import PromptGenerator
from ..statistics_tracker import StatisticsTracker


class TaskExecutionSystem:
    """Main task execution system using PhaseManager and ClaudeStreamer."""

    def __init__(self, max_tasks: int = 5):
        """
        Initialize TaskExecutionSystem

        Args:
            max_tasks: Maximum number of concurrent tasks
        """
        # Get package directory for absolute paths
        self.package_dir = Path(__file__).parent.parent

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

        # Initialize shared components
        self.statistics_tracker = StatisticsTracker("Task Execution")
        self.agent_manager = AgentManager(
            self.worker_monitor,
            self.prompt_template_dir,
            self.prompt_tmp_dir,
            self.statistics_tracker
        )
        self.prompt_generator = PromptGenerator(self.prompt_template_dir)

        # Ensure directories exist
        for dir_path in [self.prompt_tmp_dir, self.prompt_template_dir]:
            dir_path.mkdir(exist_ok=True)
        for dir_path in [self.tasks_dir, self.validation_dir, self.status_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _build_strategic_context_for_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Build strategic context for a single task (parallel worker function)."""
        try:
            strategic_context = self.phase_manager.build_strategic_context(task['id'])
            return {
                "strategic_context": strategic_context,
                "success": True
            }
        except Exception as e:
            return {
                "strategic_context": None,
                "success": False,
                "error": str(e)
            }

    def _analyze_tasks_with_strategic_context(self, available_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze tasks with strategic context in parallel

        Args:
            available_tasks: List of available tasks

        Returns:
            Enhanced tasks with strategic context
        """
        enhanced_tasks = []
        print(f"Building strategic context for {len(available_tasks)} tasks in parallel...")

        with ThreadPoolExecutor(max_workers=min(self.max_tasks, len(available_tasks))) as executor:
            # Submit all strategic context building tasks
            future_to_task = {
                executor.submit(self._build_strategic_context_for_task, task): task
                for task in available_tasks
            }

            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    task['strategic_context'] = result['strategic_context']
                    enhanced_tasks.append(task)
                    print(f"Built strategic context for task {task['id']}: {task['title']}")
                except Exception as e:
                    print(f"Warning: Failed to build strategic context for task {task['id']}: {e}")
                    task['strategic_context'] = None
                    enhanced_tasks.append(task)  # Still include task without strategic context

        return enhanced_tasks

    def _phase_1_task_analysis(self) -> bool:
        """
        Phase 1: Task Analysis - Analyze available tasks and create context files

        Returns:
            True if successful, False otherwise
        """
        print("\n--- Phase 1: Task Analysis ---")
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

        # Build strategic context for each task in parallel
        enhanced_tasks = self._analyze_tasks_with_strategic_context(tasks_to_process)

        # Run task analyzer with enhanced context
        try:
            agent_template = self.agent_manager.get_agent_template("task-analyzer-executor")
            prompt_content = self.prompt_generator.generate_task_analyzer_prompt(
                agent_template,
                enhanced_tasks
            )

            analyzer_result = self.agent_manager.process_agent_worker(
                "task-analyzer-executor",
                prompt_content,
                1,
                {'available_tasks': enhanced_tasks}
            )

            if not analyzer_result["success"]:
                print(f"[ERROR] Task analysis failed: {analyzer_result.get('error', 'Unknown error')}")
                return False

            print("[OK] Task analysis completed successfully")
            return True

        except Exception as e:
            print(f"[ERROR] Exception in task analysis: {e}")
            return False

    def _execute_single_task(self, task: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Execute a single task using ClaudeStreamer."""
        # Update worker status - starting task execution
        self.worker_monitor.update_worker(worker_id, f"Executing task {task['id']}: {task['title']}", WorkerState.ACTIVE)

        # Create enhanced prompt file with context
        prompt_content = f"""Dengan konteks lengkap dari file .ai/brain/tasks/{task['id']}.md dan @cred.md , kerjakan task tersebut.

Project Structure: .ai/structure/structure.md
Database Schema: .ai/schema/index.json

Ikuti recommendations dan existing patterns yang sudah dianalisis.
Max 300 lines per file dengan AI-friendly naming (maksudnya submodule gitu kalau lebih dari 300 line).

Execute task sekarang."""

        # Create separate ClaudeStreamer instance for this worker
        worker_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Define stream callback for worker monitoring
        stream_callback = self.agent_manager.create_stream_callback(worker_id)

        try:
            # Update worker status - calling Claude
            self.worker_monitor.update_worker(worker_id, f"Calling Claude for task {task['id']}", WorkerState.ACTIVE)

            # Create temporary prompt file for this task
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prompt_file = self.prompt_tmp_dir / f"task_execution_{task['id']}_{timestamp}.txt"

            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt_content)

            # Use file-based streaming
            response_text, exit_code = worker_streamer.get_response_from_file_with_stream(
                prompt_file, stream_callback
            )

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

        finally:
            # Clean up prompt file
            try:
                if 'prompt_file' in locals():
                    os.remove(prompt_file)
            except Exception:
                pass

        # Update statistics
        self.statistics_tracker.update_success(success)

        # Set worker back to idle when done
        if success:
            self.worker_monitor.set_worker_idle(worker_id)
        else:
            # Keep error state visible for a moment, then set to idle
            import threading
            import time

            def delayed_idle():
                time.sleep(2)  # Show error for 2 seconds
                self.worker_monitor.set_worker_idle(worker_id)

            threading.Thread(target=delayed_idle, daemon=True).start()

        # Return result
        return {
            "success": success,
            "response": response_text,
            "task": task,
            "error": error_msg
        }

    def _phase_2_task_execution(self, tasks_to_process: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Phase 2: Task Execution - Execute tasks in parallel

        Args:
            tasks_to_process: List of tasks to execute

        Returns:
            Dictionary mapping task IDs to execution results
        """
        print("\n--- Phase 2: Task Execution ---")
        print("Executing tasks in parallel...")

        task_results = {}

        with ThreadPoolExecutor(max_workers=self.max_tasks) as executor:
            # Submit all tasks to workers
            future_to_task = {
                executor.submit(self._execute_single_task, task, i+1): task
                for i, task in enumerate(tasks_to_process)
            }

            # Wait for all to complete and collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    task_results[task['id']] = result
                except Exception as e:
                    self.worker_monitor.set_worker_error(1, f"Task exception: {e}")
                    self.statistics_tracker.update_success(False)
                    task_results[task['id']] = {"success": False, "error": str(e)}

        return task_results

    def _validate_single_task(self, validation_task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single task (parallel worker function)."""
        task_id = validation_task['task_id']
        worker_id = validation_task['worker_id']

        try:
            print(f"Validating task {task_id}...")

            try:
                agent_template = self.agent_manager.get_agent_template("task-validator")
                prompt_content = self.prompt_generator.generate_task_validator_prompt(agent_template, task_id)
            except Exception as e:
                print(f"Error getting task-validator template: {e}")
                return {"validation_status": "FAIL", "success": False, "error": str(e)}

            validator_result = self.agent_manager.process_agent_worker(
                "task-validator",
                prompt_content,
                worker_id
            )

            # Extract validation status from response
            validation_status = "FAIL"  # Default
            if validator_result.get("success"):
                response = validator_result.get("response", "")
                if "PASS" in response:
                    validation_status = "PASS"
                elif "PARTIAL" in response:
                    validation_status = "PARTIAL"

            return {
                "validation_status": validation_status,
                "success": True
            }
        except Exception as e:
            return {
                "validation_status": "FAIL",
                "success": False,
                "error": str(e)
            }

    def _phase_3_quality_validation(self, task_results: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Phase 3: Quality Validation - Validate task implementations in parallel

        Args:
            task_results: Results from task execution phase

        Returns:
            Dictionary mapping task IDs to validation results
        """
        print("\n--- Phase 3: Quality Validation ---")
        print("Running task-validator agent in parallel...")

        validation_results = {}
        validation_tasks = []

        # Prepare validation tasks for successful executions
        for task_id, task_result in task_results.items():
            if task_result.get("success", False):
                validation_tasks.append({
                    'task_id': task_id,
                    'worker_id': len(validation_tasks) + 1
                })
                validation_results[task_id] = "PENDING"
            else:
                validation_results[task_id] = "FAIL"
                print(f"[ERROR] Task {task_id} execution failed, skipping validation")

        # Run validations in parallel
        if validation_tasks:
            with ThreadPoolExecutor(max_workers=min(self.max_tasks, len(validation_tasks))) as executor:
                # Submit all validation tasks
                future_to_validation = {
                    executor.submit(self._validate_single_task, task): task
                    for task in validation_tasks
                }

                # Collect results
                for future in as_completed(future_to_validation):
                    validation_task = future_to_validation[future]
                    task_id = validation_task['task_id']
                    try:
                        result = future.result()
                        validation_results[task_id] = result['validation_status']

                        if result['validation_status'] == "PASS":
                            print(f"[OK] Task {task_id} validation PASSED")
                        elif result['validation_status'] == "PARTIAL":
                            print(f"[WARNING] Task {task_id} validation PARTIAL")
                        else:
                            print(f"[ERROR] Task {task_id} validation FAILED")
                    except Exception as e:
                        validation_results[task_id] = "FAIL"
                        print(f"[ERROR] Task {task_id} validation exception: {e}")

        return validation_results

    def _update_single_task_status(self, status_task: Dict[str, Any]) -> Dict[str, Any]:
        """Update status for a single task (parallel worker function)."""
        task_id = status_task['task_id']
        validation_result = status_task['validation_result']
        worker_id = status_task['worker_id']

        try:
            try:
                agent_template = self.agent_manager.get_agent_template("task-status-updater")
                prompt_content = self.prompt_generator.generate_task_status_updater_prompt(
                    agent_template,
                    task_id,
                    validation_result
                )
            except Exception as e:
                print(f"Error getting task-status-updater template: {e}")
                return {"success": False, "error": str(e)}

            updater_result = self.agent_manager.process_agent_worker(
                "task-status-updater",
                prompt_content,
                worker_id
            )

            return {
                "success": updater_result.get("success", False),
                "error": updater_result.get("error")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _phase_4_status_management(self, validation_results: Dict[str, str]) -> int:
        """
        Phase 4: Status Management - Update task statuses based on validation results

        Args:
            validation_results: Results from validation phase

        Returns:
            Number of successfully updated tasks
        """
        print("\n--- Phase 4: Status Management ---")
        print("Running task-status-updater agent in parallel...")

        status_updated = 0
        status_tasks = []

        # Prepare status update tasks for all validation results
        for task_id, validation_result in validation_results.items():
            status_tasks.append({
                'task_id': task_id,
                'validation_result': validation_result,
                'worker_id': len(status_tasks) + 1
            })

        # Run status updates in parallel
        if status_tasks:
            with ThreadPoolExecutor(max_workers=min(self.max_tasks, len(status_tasks))) as executor:
                # Submit all status update tasks
                future_to_status = {
                    executor.submit(self._update_single_task_status, task): task
                    for task in status_tasks
                }

                # Collect results
                for future in as_completed(future_to_status):
                    status_task = future_to_status[future]
                    task_id = status_task['task_id']
                    validation_result = status_task['validation_result']
                    try:
                        result = future.result()
                        if result.get("success"):
                            status_updated += 1
                            new_status = "completed" if validation_result == "PASS" else "in-progress"
                            print(f"[OK] Task {task_id} status updated to {new_status}")
                        else:
                            print(f"[ERROR] Failed to update status for task {task_id}: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"[ERROR] Task {task_id} status update exception: {e}")

        return status_updated

    def run_task_execution(self, max_tasks: int = 5) -> bool:
        """
        Run the complete task execution process.

        Args:
            max_tasks: Maximum number of concurrent tasks

        Returns:
            True if successful, False otherwise
        """
        self.max_tasks = max_tasks
        self.statistics_tracker.start_timing()

        print(f"Starting Task Execution System")
        print(f"Maximum concurrent tasks: {self.max_tasks}")
        print(f"Output directories: {self.brain_dir}")

        # Start worker monitoring display
        self.worker_monitor.start_display()

        try:
            # Phase 1: Task Analysis
            if not self._phase_1_task_analysis():
                return False

            # Get tasks to process (re-fetch after analysis)
            available_tasks = self.phase_manager.get_workable_phases()
            tasks_to_process = available_tasks[:self.max_tasks]

            if not tasks_to_process:
                print("[OK] No tasks to execute")
                return True

            # Phase 2: Task Execution (Parallel)
            task_results = self._phase_2_task_execution(tasks_to_process)

            # Phase 3: Quality Validation (Parallel)
            validation_results = self._phase_3_quality_validation(task_results)

            # Phase 4: Status Management (Parallel)
            status_updated = self._phase_4_status_management(validation_results)

            # Final summary
            print(f"\n--- Task Execution Summary ---")
            self.statistics_tracker.print_summary()
            print(f"Status updated: {status_updated}")

            if self.statistics_tracker.failed_items == 0:
                print("[OK] Task execution completed successfully!")
                return True
            else:
                print("[ERROR] Task execution completed with errors")
                return False

        except KeyboardInterrupt:
            from ..shared_helpers import handle_keyboard_interrupt
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_keyboard_interrupt(stats_dict, "Task execution")
            return False
        except Exception as e:
            from ..shared_helpers import handle_fatal_error
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_fatal_error(e, stats_dict, "Task execution")
            return False
        finally:
            # Stop worker monitoring display
            self.worker_monitor.stop_display()