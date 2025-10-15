#!/usr/bin/env python3
"""
Breakdown Loop - Python Implementation

Automated breakdown analyzer that uses PhaseManager and ClaudeStreamer
to break down phases with duration >60 minutes into manageable sub-phases.
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
    from phase_manager import PhaseManager
except ImportError as e:
    print(f"Error importing classes: {e}")
    print(f"Make sure {class_dir} contains claude_streamer.py and phase_manager.py")
    sys.exit(1)


class BreakdownLoop:
    """Main breakdown loop system using PhaseManager and ClaudeStreamer."""

    def __init__(self, max_workers: int = 1):
        """
        Initialize BreakdownLoop

        Args:
            max_workers: Number of parallel workers for processing phases
        """
        self.plan_dir = Path(".ai/plan")
        self.prompt_tmp_dir = Path("prompt_tmp")
        self.prompt_template_dir = Path("prompt_template")
        self.max_workers = max_workers

        # Initialize managers
        self.phase_manager = PhaseManager(str(self.plan_dir))
        self.claude_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Ensure directories exist
        self.prompt_tmp_dir.mkdir(exist_ok=True)
        self.prompt_template_dir.mkdir(exist_ok=True)
        self.plan_dir.mkdir(parents=True, exist_ok=True)

        # Statistics tracking
        self.total_processed = 0
        self.successful_breakdowns = 0
        self.failed_breakdowns = 0
        self.start_time = None

  
    def _create_prompt_file(self, phase_info: Dict[str, Any]) -> str:
        """
        Create a compact prompt file for breakdown agent.

        Args:
            phase_info: Information about the phase to breakdown

        Returns:
            Path to created prompt file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = self.prompt_tmp_dir / f"breakdown_{phase_info['phase_id']}_{timestamp}.txt"

        # Read the plan-breakdown-analyzer agent template
        agent_content = self._get_agent_template()

        # Create focused prompt for this specific phase
        prompt = f"""You are plan-breakdown-analyzer agent.

{agent_content}

## TASK: Breakdown this phase

**Phase Information:**
- Phase ID: {phase_info['phase_id']}
- Title: {phase_info['title']}
- Duration: {phase_info['duration']} minutes
- Status: {phase_info['status']}
- Source File: {phase_info['file']}

**Instructions:**
1. This phase duration is >60 minutes and needs breakdown
2. Create sub-phases with duration <60 minutes each
3. Generate single file: {phase_info['phase_id']}.json
4. Use dependency-based breakdown approach
5. Include all sub-phases in the single file
6. Set breakdown_complete: true when done

**Output Location:**
Save the result to: {self.plan_dir}/{phase_info['phase_id']}.json

Please proceed with the breakdown now.
"""

        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            return str(prompt_file)
        except Exception as e:
            print(f"Error creating prompt file: {e}")
            return ""

    def _get_agent_template(self) -> str:
        """Get the plan-breakdown-analyzer agent template."""
        agent_file = self.prompt_template_dir / "plan-breakdown-analyzer.md"

        if not agent_file.exists():
            raise FileNotFoundError(f"Prompt template not found: {agent_file}")

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

    def _call_breakdown_agent(self, phase_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call breakdown agent via ClaudeStreamer.

        Args:
            phase_info: Information about the phase to breakdown

        Returns:
            Result dictionary with success status and details
        """
        print(f"\n[PROCESS] Phase {phase_info['phase_id']}: {phase_info['title']}")
        print(f"   Duration: {phase_info['duration']} minutes")
        print(f"   File: {phase_info['file']}")

        # Create prompt file
        prompt_file = self._create_prompt_file(phase_info)
        if not prompt_file:
            return {
                "success": False,
                "error": "Failed to create prompt file",
                "phase_id": phase_info['phase_id']
            }

        print(f"   Created prompt: {prompt_file}")

        # Call Claude via ClaudeStreamer - gunakan @file syntax
        print(f"   Sending to Claude...")

        # Initialize response variables
        response_text = ""
        exit_code = -1
        success = False
        error_msg = ""

        try:
            # Kirim prompt file langsung dengan @file syntax
            response_text, exit_code = self.claude_streamer.get_response_from_file(prompt_file)
            print(f"   [DEBUG] Response length: {len(response_text)} chars")
            print(f"   [DEBUG] Exit code: {exit_code}")

            if exit_code == 0:
                print(f"   [OK] Claude response received")
                success = True
            else:
                print(f"   [ERROR] Claude error (exit code: {exit_code})")
                print(f"   [DEBUG] Response: {response_text[:500]}")
                error_msg = f"Claude returned exit code {exit_code}"

        except Exception as e:
            print(f"   [ERROR] Exception calling Claude: {e}")
            error_msg = f"Exception: {e}"

        finally:
            # Always clean up prompt file regardless of success/failure
            try:
                os.remove(prompt_file)
                print(f"   [CLEANUP] Removed prompt file: {prompt_file}")
            except Exception as cleanup_error:
                print(f"   [WARNING] Failed to remove prompt file: {cleanup_error}")

        # Return result
        if success:
            return {
                "success": True,
                "response": response_text,
                "phase_id": phase_info['phase_id'],
                "prompt_file": prompt_file
            }
        else:
            return {
                "success": False,
                "error": error_msg,
                "response": response_text,
                "phase_id": phase_info['phase_id']
            }

    def _update_statistics(self, success: bool):
        """Update processing statistics."""
        self.total_processed += 1
        if success:
            self.successful_breakdowns += 1
        else:
            self.failed_breakdowns += 1

    def _print_statistics(self):
        """Print current statistics."""
        print(f"\n[STATISTICS]:")
        print(f"   Total processed: {self.total_processed}")
        print(f"   Successful: {self.successful_breakdowns}")
        print(f"   Failed: {self.failed_breakdowns}")
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            print(f"   Elapsed time: {elapsed}")

    def _process_phase_worker(self, phase_info: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """
        Worker function to process a single phase.

        Args:
            phase_info: Information about the phase to breakdown
            worker_id: ID of the worker processing this phase

        Returns:
            Result dictionary with success status and details
        """
        print(f"[WORKER-{worker_id}] Starting Phase {phase_info['phase_id']}: {phase_info['title']}")

        # Add small random delay to prevent all workers hitting Claude at once
        if self.max_workers > 1:
            initial_delay = random.uniform(0.1, 0.5) * worker_id
            if initial_delay > 0:
                print(f"[WORKER-{worker_id}] Delaying {initial_delay:.1f}s to prevent rate limiting...")
                time.sleep(initial_delay)

        # Call breakdown agent
        result = self._call_breakdown_agent(phase_info)

        # Update statistics
        self._update_statistics(result["success"])

        # Show result
        if result["success"]:
            print(f"[WORKER-{worker_id}] [OK] Completed Phase {phase_info['phase_id']}")
        else:
            print(f"[WORKER-{worker_id}] [ERROR] Failed Phase {phase_info['phase_id']}: {result.get('error', 'Unknown error')}")

        return result

    def run_loop(self, max_iterations: int = 50):
        """
        Run the main breakdown loop with parallel processing.

        Args:
            max_iterations: Maximum number of iterations to prevent infinite loops
        """
        if not self.start_time:
            self.start_time = datetime.now()
            self.total_processed = 0
            self.successful_breakdowns = 0
            self.failed_breakdowns = 0

        print(f"\n[START] Starting Breakdown Loop")
        print(f"   Plan directory: {self.plan_dir}")
        print(f"   Prompt temp directory: {self.prompt_tmp_dir}")
        print(f"   Max workers: {self.max_workers}")
        print(f"   Max iterations: {max_iterations}")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"[LOOP] Iteration {iteration}")
            print(f"{'='*60}")

            # Find phases needing breakdown
            phases_needing_breakdown = self.phase_manager.find_phases_needing_breakdown(limit=50)

            if not phases_needing_breakdown:
                print("[SUCCESS] No phases with duration >60 minutes need breakdown!")
                print("[SUCCESS] All leaf phases are within the required duration limit.")
                self._print_statistics()
                print("\n[DONE] Breakdown loop completed successfully!")
                break

            print(f"[FOUND] {len(phases_needing_breakdown)} phases needing breakdown:")

            # Group by file for display
            grouped_by_file = {}
            for phase in phases_needing_breakdown:
                file_name = phase['file']
                if file_name not in grouped_by_file:
                    grouped_by_file[file_name] = []
                grouped_by_file[file_name].append(phase)

            # Display found phases
            for file_name, phases in grouped_by_file.items():
                print(f"\n[FILE] File: {file_name}")
                for phase in phases:
                    print(f"   - Phase {phase['phase_id']}: {phase['title']}")
                    print(f"     Duration: {phase['duration']} minutes | Status: {phase['status']}")
                    self.phase_manager.log_duration_check(phase['phase_id'], phase['duration'])

            # Process phases in parallel
            print(f"\n[PARALLEL] Processing {len(phases_needing_breakdown)} phases with {self.max_workers} workers...")

            # Determine number of phases to process in this batch
            # Process up to max_workers phases per iteration
            phases_to_process = phases_needing_breakdown[:self.max_workers]

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all phases to workers
                future_to_phase = {
                    executor.submit(self._process_phase_worker, phase, i+1): phase
                    for i, phase in enumerate(phases_to_process)
                }

                # Wait for all to complete
                for future in as_completed(future_to_phase):
                    phase = future_to_phase[future]
                    try:
                        result = future.result()
                        # Results are already handled in _process_phase_worker
                    except Exception as e:
                        print(f"[ERROR] Worker exception for phase {phase['phase_id']}: {e}")
                        self._update_statistics(False)

            print(f"\n[BATCH] Completed batch. Processed {len(phases_to_process)} phases.")
            self._print_statistics()

        else:
            print(f"\n[STOP] Maximum iterations ({max_iterations}) reached. Stopping loop.")
            self._print_statistics()

        print(f"\n[DONE] Breakdown loop finished!")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Breakdown Loop - Automated Phase Breakdown System")
    parser.add_argument("--max-iterations", type=int, default=50,
                       help="Maximum iterations to prevent infinite loops (default: 50)")
    parser.add_argument("--workers", type=int, default=1,
                       help="Number of parallel workers for processing phases (default: 1)")

    args = parser.parse_args()

    # Initialize breakdown loop
    breakdown_loop = BreakdownLoop(max_workers=args.workers)

    # Run the loop
    try:
        breakdown_loop.run_loop(max_iterations=args.max_iterations)
    except KeyboardInterrupt:
        print(f"\n\n[INTERRUPTED] Breakdown interrupted by user")
        breakdown_loop._print_statistics()
    except Exception as e:
        print(f"\n\n[FATAL ERROR] Unexpected error: {e}")
        breakdown_loop._print_statistics()


if __name__ == "__main__":
    main()