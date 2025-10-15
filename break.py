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
        for dir_path in [self.prompt_tmp_dir, self.prompt_template_dir]:
            dir_path.mkdir(exist_ok=True)
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
            print(f"✗ Error creating prompt file: {e}")
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
        print(f"Phase {phase_info['phase_id']}: {phase_info['title']} ({phase_info['duration']} min)")

        # Create prompt file
        prompt_file = self._create_prompt_file(phase_info)
        if not prompt_file:
            return {
                "success": False,
                "error": "Failed to create prompt file",
                "phase_id": phase_info['phase_id']
            }

        try:
            # Kirim prompt file langsung dengan @file syntax
            response_text, exit_code = self.claude_streamer.get_response_from_file(prompt_file)

            if exit_code == 0:
                print(f"   ✓ Success")
                success = True
            else:
                print(f"   ✗ Claude error (exit code: {exit_code})")
                error_msg = f"Claude returned exit code {exit_code}"

        except Exception as e:
            print(f"   ✗ Exception: {e}")
            error_msg = f"Exception: {e}"

        finally:
            # Clean up prompt file
            try:
                os.remove(prompt_file)
            except Exception:
                pass

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

    def _process_phase_worker(self, phase_info: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Worker function to process a single phase."""
        print(f"Worker-{worker_id}: {phase_info['phase_id']}")

        # Call breakdown agent
        result = self._call_breakdown_agent(phase_info)

        # Update statistics
        self._update_statistics(result["success"])

        # Show result
        if result["success"]:
            print(f"   ✓ Completed")
        else:
            print(f"   ✗ Failed: {result.get('error', 'Unknown error')}")

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

        print(f"Starting Breakdown Loop - Workers: {self.max_workers}, Iterations: {max_iterations}")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")

            # Find phases needing breakdown
            phases_needing_breakdown = self.phase_manager.find_phases_needing_breakdown(limit=50)

            if not phases_needing_breakdown:
                print("✓ No phases need breakdown - all within 60min limit")
                print(f"Stats: {self.successful_breakdowns} success, {self.failed_breakdowns} failed")
                print("\n✓ Breakdown loop completed!")
                break

            print(f"Found {len(phases_needing_breakdown)} phases needing breakdown:")

            # Group by file for display
            grouped_by_file = {}
            for phase in phases_needing_breakdown:
                file_name = phase['file']
                if file_name not in grouped_by_file:
                    grouped_by_file[file_name] = []
                grouped_by_file[file_name].append(phase)

            # Display found phases
            for file_name, phases in grouped_by_file.items():
                print(f"\nFile: {file_name}")
                for phase in phases:
                    print(f"   - {phase['phase_id']}: {phase['title']} ({phase['duration']}min)")

            print(f"\nProcessing {len(phases_needing_breakdown)} phases with {self.max_workers} workers...")

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
                        print(f"   ✗ Worker exception: {e}")
                        self._update_statistics(False)

            print(f"Batch completed: {len(phases_to_process)} phases processed")
            print(f"Stats: {self.successful_breakdowns} success, {self.failed_breakdowns} failed")

        else:
            print(f"\n✓ Maximum iterations ({max_iterations}) reached")
            print(f"Final stats: {self.successful_breakdowns} success, {self.failed_breakdowns} failed")

        print("\n✓ Breakdown loop finished!")


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
        print(f"\n\n✓ Interrupted by user")
        print(f"Stats: {breakdown_loop.successful_breakdowns} success, {breakdown_loop.failed_breakdowns} failed")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        print(f"Stats: {breakdown_loop.successful_breakdowns} success, {breakdown_loop.failed_breakdowns} failed")


if __name__ == "__main__":
    main()