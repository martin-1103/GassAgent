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

    def __init__(self, plan_dir: str = ".ai/plan", prompt_tmp_dir: str = "prompt_tmp", prompt_template_dir: str = "prompt_template", max_workers: int = 1):
        """
        Initialize BreakdownLoop

        Args:
            plan_dir: Directory containing plan JSON files
            prompt_tmp_dir: Directory for temporary prompt files
            prompt_template_dir: Directory for prompt templates
            max_workers: Number of parallel workers for processing phases
        """
        self.plan_dir = Path(plan_dir)
        self.prompt_tmp_dir = Path(prompt_tmp_dir)
        self.prompt_template_dir = Path(prompt_template_dir)
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
        try:
            # Kirim prompt file langsung dengan @file syntax
            response_text, exit_code = self.claude_streamer.get_response_from_file(prompt_file)
            print(f"   [DEBUG] Response length: {len(response_text)} chars")
            print(f"   [DEBUG] Exit code: {exit_code}")

            if exit_code == 0:
                print(f"   [OK] Claude response received")

                # Clean up prompt file
                try:
                    os.remove(prompt_file)
                except:
                    pass

                return {
                    "success": True,
                    "response": response_text,
                    "phase_id": phase_info['phase_id'],
                    "prompt_file": prompt_file
                }
            else:
                print(f"   [ERROR] Claude error (exit code: {exit_code})")
                print(f"   [DEBUG] Response: {response_text[:500]}")
                return {
                    "success": False,
                    "error": f"Claude returned exit code {exit_code}",
                    "response": response_text,
                    "phase_id": phase_info['phase_id']
                }

        except Exception as e:
            print(f"   [ERROR] Exception calling Claude: {e}")
            return {
                "success": False,
                "error": f"Exception: {e}",
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
        log = self.breakdown_log
        print(f"\n[STATISTICS]:")
        print(f"   Total processed: {log['total_processed']}")
        print(f"   Successful: {log['successful_breakdowns']}")
        print(f"   Failed: {log['failed_breakdowns']}")
        if log['last_run']:
            print(f"   Last run: {log['last_run']}")

    def run_loop(self, reset: bool = False, max_iterations: int = 50):
        """
        Run the main breakdown loop.

        Args:
            reset: Clear log and start fresh
            max_iterations: Maximum number of iterations to prevent infinite loops
        """
        if reset:
            print("[RESET] Resetting breakdown log...")
            self.breakdown_log = {
                "start_time": datetime.now().isoformat(),
                "last_run": None,
                "total_processed": 0,
                "successful_breakdowns": 0,
                "failed_breakdowns": 0,
                "sessions": []
            }
            self._save_log()
            print("   [OK] Log reset complete")

        print(f"\n[START] Starting Breakdown Loop")
        print(f"   Plan directory: {self.plan_dir}")
        print(f"   Prompt temp directory: {self.prompt_tmp_dir}")
        print(f"   Max iterations: {max_iterations}")

        iteration = 0
        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*60}")
            print(f"[LOOP] Iteration {iteration}")
            print(f"{'='*60}")

            # Find phases needing breakdown
            phases_needing_breakdown = self.phase_manager.find_phases_needing_breakdown(limit=20)

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

            # Process first phase
            first_phase = phases_needing_breakdown[0]
            print(f"\n[PROCESSING] Phase {first_phase['phase_id']} ({first_phase['title']})")

            # Call breakdown agent
            result = self._call_breakdown_agent(first_phase)

            # Update log
            self._update_log(result)

            # Show result
            if result["success"]:
                print(f"   [OK] Breakdown completed for phase {first_phase['phase_id']}")
            else:
                print(f"   [ERROR] Breakdown failed for phase {first_phase['phase_id']}: {result.get('error', 'Unknown error')}")

            # Brief pause between iterations
            time.sleep(2)

        else:
            print(f"\n[STOP] Maximum iterations ({max_iterations}) reached. Stopping loop.")
            self._print_statistics()

        print(f"\n[LOG] Final breakdown log saved to: {self.log_file}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="Breakdown Loop - Automated Phase Breakdown System")
    parser.add_argument("--plan-dir", default=".ai/plan",
                       help="Plan directory path (default: .ai/plan)")
    parser.add_argument("--prompt-dir", default="prompt_tmp",
                       help="Prompt temporary directory (default: prompt_tmp)")
    parser.add_argument("--template-dir", default="prompt_template",
                       help="Prompt template directory (default: prompt_template)")
    parser.add_argument("--reset", action="store_true",
                       help="Reset breakdown log and start fresh")
    parser.add_argument("--max-iterations", type=int, default=50,
                       help="Maximum iterations to prevent infinite loops (default: 50)")
    parser.add_argument("--workers", type=int, default=1,
                       help="Number of parallel workers for processing phases (default: 1)")
    parser.add_argument("--stats-only", action="store_true",
                       help="Show only current statistics")

    args = parser.parse_args()

    # Initialize breakdown loop
    breakdown_loop = BreakdownLoop(
        plan_dir=args.plan_dir,
        prompt_tmp_dir=args.prompt_dir,
        prompt_template_dir=args.template_dir
    )

    if args.stats_only:
        breakdown_loop._print_statistics()
        return

    # Run the loop
    try:
        breakdown_loop.run_loop(
            reset=args.reset,
            max_iterations=args.max_iterations
        )
    except KeyboardInterrupt:
        print(f"\n\n[INTERRUPTED] Breakdown interrupted by user")
        breakdown_loop._print_statistics()
    except Exception as e:
        print(f"\n\n[FATAL ERROR] Unexpected error: {e}")
        breakdown_loop._print_statistics()


if __name__ == "__main__":
    main()