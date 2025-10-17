#!/usr/bin/env python3
"""
Breakdown System

Core breakdown system extracted from break.py
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..claude_streamer import ClaudeStreamer
from ..worker_monitor import WorkerMonitor, WorkerState
from .phase_manager import PhaseManager
from ..agent_manager import AgentManager
from ..statistics_tracker import StatisticsTracker


class BreakdownSystem:
    """Main breakdown system using PhaseManager and ClaudeStreamer."""

    def __init__(self, max_workers: int = 1):
        """
        Initialize BreakdownSystem

        Args:
            max_workers: Number of parallel workers for processing phases
        """
        # Get package directory for absolute paths
        self.package_dir = Path(__file__).parent.parent

        # Project files remain in current working directory
        self.plan_dir = Path(".ai/plan")

        # Template and temp files use package directory
        self.prompt_template_dir = self.package_dir / "prompt_template"
        self.prompt_tmp_dir = self.package_dir / "prompt_tmp"

        self.max_workers = max_workers

        # Initialize worker monitor
        self.worker_monitor = WorkerMonitor(max_workers=max_workers)

        # Initialize managers
        self.phase_manager = PhaseManager(str(self.plan_dir))
        self.claude_streamer = ClaudeStreamer(
            permission_mode="acceptEdits",
            output_format="stream-json",
            verbose=True
        )

        # Initialize shared components
        self.statistics_tracker = StatisticsTracker("Breakdown")
        self.agent_manager = AgentManager(
            self.worker_monitor,
            self.prompt_template_dir,
            self.prompt_tmp_dir,
            self.statistics_tracker
        )

        # Ensure directories exist
        for dir_path in [self.prompt_tmp_dir, self.prompt_template_dir]:
            dir_path.mkdir(exist_ok=True)
        self.plan_dir.mkdir(parents=True, exist_ok=True)

    def _format_strategic_context(self, context: Dict[str, Any]) -> str:
        """Format strategic context for prompt inclusion with expert analysis guidance"""
        formatted = []

        # Project Strategic DNA
        dna = context.get('strategic_dna', {})
        formatted.append("### PROJECT STRATEGIC DNA")
        formatted.append(f"**Vision**: {dna.get('project_vision', 'Unknown')}")
        formatted.append(f"**Goal**: {dna.get('project_goal', 'No goal specified')}")
        formatted.append(f"**Type**: {dna.get('project_type', 'unknown')}")
        formatted.append(f"**Complexity**: {dna.get('complexity', 'medium')}")

        principles = dna.get('architectural_principles', [])
        if principles:
            formatted.append(f"**Architectural Principles**: {', '.join(principles)}")

        success_factors = dna.get('critical_success_factors', [])
        if success_factors:
            formatted.append(f"**Critical Success Factors**: {', '.join(success_factors)}")

        # Expert Analysis Context
        formatted.append("\n### EXPERT ANALYSIS CONTEXT")
        project_type = dna.get('project_type', '').lower()
        complexity = dna.get('complexity', '').lower()

        # Determine domain expert focus
        domain_expert_focus = []
        if 'web' in project_type or 'app' in project_type:
            domain_expert_focus.extend(["Frontend Expert (UX/UI, Performance)", "Backend Expert (API, Business Logic)"])
        if 'api' in project_type:
            domain_expert_focus.extend(["API Expert (REST, Contracts)", "Integration Expert (Third-party APIs)"])
        if 'enterprise' in complexity:
            domain_expert_focus.extend(["Database Expert (Scalability, Performance)", "Testing Expert (Comprehensive Coverage)"])
        if 'mobile' in project_type:
            domain_expert_focus.extend(["Mobile Expert (Platform Guidelines)", "Performance Expert (Resource Optimization)"])

        # Always include core experts
        formatted.append("**Core Experts (Always Active)**:")
        formatted.append("  - Performance Expert: Computational efficiency, scalability, resource optimization")
        formatted.append("  - Security Expert: Security implications, vulnerability assessment, data protection")
        formatted.append("  - Architecture Expert: Structural consistency, maintainability, design patterns")

        # Add domain-specific experts
        if domain_expert_focus:
            formatted.append("**Domain Experts (Based on Project Type)**:")
            for expert in domain_expert_focus:
                formatted.append(f"  - {expert}")

        # Expert priority concerns based on project characteristics
        formatted.append("\n**Expert Priority Concerns**:")
        if 'performance' in ' '.join(principles).lower() or 'scalability' in ' '.join(success_factors).lower():
            formatted.append("  - PERFORMANCE Expert has HIGH priority (performance is critical success factor)")
        if 'security' in ' '.join(principles).lower() or 'security' in ' '.join(success_factors).lower():
            formatted.append("  - SECURITY Expert has HIGH priority (security is critical success factor)")
        if 'enterprise' in complexity:
            formatted.append("  - ARCHITECTURE Expert has HIGH priority (enterprise complexity requires strong structure)")
            formatted.append("  - TESTING Expert has elevated priority (enterprise requires comprehensive coverage)")

        # Parent Chain
        parent_chain = context.get('parent_chain', [])
        if parent_chain:
            formatted.append("\n### PARENT CHAIN (Hierarchy of Goals)")
            for parent in parent_chain:
                level_indicator = "  " * parent.get('level', 0)
                parent_id = parent.get('id', 'unknown')
                if parent_id == 'project':
                    # Project root - use phases.json
                    formatted.append(f"{level_indicator}**Level {parent.get('level', 0)}**: @.ai/plan/phases.json - {parent.get('title', 'Unknown')}")
                else:
                    # Regular parent phase
                    formatted.append(f"{level_indicator}**Level {parent.get('level', 0)}**: @.ai/plan/{parent_id}.json - {parent.get('title', 'Unknown')}")
                formatted.append(f"{level_indicator}  Goal: {parent.get('goal', 'No goal specified')}")
                if parent.get('deliverables'):
                    formatted.append(f"{level_indicator}  Key Deliverables: {', '.join(parent['deliverables'][:3])}")

        # Sibling Coordination
        coordination = context.get('sibling_coordination', {})
        if coordination.get('has_siblings'):
            formatted.append("\n### SIBLING COORDINATION REQUIREMENTS")
            coordination_points = coordination.get('coordination_points', [])
            for point in coordination_points:
                sibling_id = point.get('sibling_id', 'Unknown')
                formatted.append(f"**Sibling @.ai/plan/{sibling_id}.json**: {point.get('sibling_title', 'Unknown')}")
                formatted.append(f"  - Coordination Type: {point.get('coordination_type', 'unknown')}")
                formatted.append(f"  - Notes: {point.get('dependency_notes', 'No coordination notes')}")

            # Expert guidance for coordination
            formatted.append("\n**Expert Coordination Guidance**:")
            formatted.append("  - INTEGRATION Expert: Focus on API contracts and data flow compatibility")
            formatted.append("  - ARCHITECTURE Expert: Ensure consistent patterns across sibling implementations")
            formatted.append("  - PERFORMANCE Expert: Consider performance implications of coordination overhead")

        # Boundary Constraints
        constraints = context.get('boundary_constraints', {})
        formatted.append("\n### BOUNDARY CONSTRAINTS")

        must_include = constraints.get('must_include', [])
        if must_include:
            formatted.append("**MUST INCLUDE**: " + ", ".join(must_include))
            formatted.append("**Expert Validation Required**: All experts must validate these requirements are met")

        must_not_include = constraints.get('must_not_include', [])
        if must_not_include:
            formatted.append("**MUST NOT INCLUDE**: " + ", ".join(must_not_include))
            formatted.append("**Expert Watch List**: Security and Architecture experts must monitor for violations")

        scope_limits = constraints.get('scope_limits', [])
        if scope_limits:
            formatted.append("**SCOPE LIMITS**: " + ", ".join(scope_limits))
            formatted.append("**Expert Focus**: Domain and Architecture experts should validate scope adherence")

        # Current Phase Context
        current = context.get('current_phase', {})
        formatted.append(f"\n### CURRENT PHASE CONTEXT")
        formatted.append(f"**Phase**: @.ai/plan/{current.get('id', 'unknown')}.json - {current.get('title', 'Unknown')}")
        formatted.append(f"**Description**: {current.get('description', 'No description available')}")
        if current.get('deliverables'):
            formatted.append(f"**Expected Deliverables**: {', '.join(current['deliverables'])}")

        # Expert-specific guidance for current phase
        formatted.append("\n**Expert Analysis Focus for This Phase**:")
        formatted.append("  - PERFORMANCE Expert: Analyze scalability and efficiency implications")
        formatted.append("  - SECURITY Expert: Identify security risks and mitigation requirements")
        formatted.append("  - ARCHITECTURE Expert: Validate structural consistency and integration points")
        if 'database' in current.get('description', '').lower():
            formatted.append("  - DATABASE Expert: Schema design and query optimization focus")
        if 'api' in current.get('description', '').lower():
            formatted.append("  - API Expert: Contract design and versioning considerations")
        if 'test' in current.get('description', '').lower():
            formatted.append("  - TESTING Expert: Test strategy and coverage requirements")

        return "\n".join(formatted)

    def _create_enhanced_prompt_file(self, phase_info: Dict[str, Any]) -> str:
        """
        Create enhanced prompt file with strategic context for breakdown agent.

        Args:
            phase_info: Information about the phase to breakdown

        Returns:
            Path to created prompt file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_file = self.prompt_tmp_dir / f"breakdown_{phase_info['phase_id']}_{timestamp}.txt"

        # Read the enhanced plan-breakdown-analyzer agent template
        try:
            agent_content = self.agent_manager.get_agent_template("plan-breakdown-analyzer")
        except Exception as e:
            print(f"Error getting plan-breakdown-analyzer template: {e}")
            return ""

        # Build complete strategic context for this phase
        strategic_context = self.phase_manager.build_strategic_context(phase_info['phase_id'])

        # Format strategic context for prompt
        formatted_context = self._format_strategic_context(strategic_context)

        # Create enhanced prompt with strategic context
        prompt = f"""You are plan-breakdown-analyzer agent with strategic context awareness.

{agent_content}

## STRATEGIC CONTEXT (MANDATORY ANALYSIS REQUIRED)

{formatted_context}

## TASK: Strategic-Guided Breakdown

**Target Phase Information:**
- Phase ID: {phase_info['phase_id']}
- Title: {phase_info['title']}
- Duration: {phase_info['duration']} minutes
- Status: {phase_info['status']}
- Source File: @.ai/plan/{phase_info['file']}

**STRATEGIC BREAKDOWN INSTRUCTIONS:**
1. **CONTEXT ANALYSIS**: Thoroughly analyze the strategic context provided ABOVE before breakdown
2. **ALIGNMENT CHECK**: Ensure all sub-phases align with project vision and parent goals
3. **BOUNDARY COMPLIANCE**: Respect all MUST/MUST_NOT constraints and scope limitations
4. **COORDINATION PLANNING**: Include coordination phases for sibling alignment if needed
5. **ARCHITECTURAL CONSISTENCY**: Maintain architectural principles throughout breakdown
6. **DURATION CONSTRAINT**: Create sub-phases with duration <60 minutes each
7. **SINGLE FILE OUTPUT**: Generate single file: {phase_info['phase_id']}.json
8. **COMPLETE BREAKDOWN**: Include all sub-phases in the single file with strategic alignment
9. **QUALITY VALIDATION**: Set breakdown_complete: true only after strategic validation

**OUTPUT REQUIREMENTS:**
- Save to: {self.plan_dir}/{phase_info['phase_id']}.json
- All sub-phases must support strategic goals from context analysis
- Include coordination considerations if siblings exist
- Respect boundary constraints from parent chain
- Maintain architectural consistency

Please proceed with strategic-guided breakdown now.
"""

        try:
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            return str(prompt_file)
        except Exception as e:
            print(f"✗ Error creating enhanced prompt file: {e}")
            return ""

    def _validate_breakdown_result(self, response_text: str, strategic_context: Dict[str, Any], phase_id: str) -> Dict[str, Any]:
        """
        Validate breakdown result against strategic context using smart constraint engine.

        Args:
            response_text: The breakdown response text from Claude
            strategic_context: The strategic context used for breakdown
            phase_id: The phase ID for validation

        Returns:
            Validation result with scoring and recommendations
        """
        try:
            # Try to parse response as JSON
            breakdown_result = json.loads(response_text)

            # Use PhaseManager's validation system
            validation = self.phase_manager.validate_breakdown_alignment(breakdown_result, strategic_context)

            # Log validation results
            if validation["is_valid"]:
                print(f"✓ Phase {phase_id} validation PASSED (Score: {validation['overall_score']}/100)")
            else:
                print(f"✗ Phase {phase_id} validation FAILED (Score: {validation['overall_score']}/100)")
                for rec in validation["recommendations"][:3]:  # Show top 3 recommendations
                    print(f"  - {rec}")

            return validation

        except json.JSONDecodeError as e:
            # JSON parsing failed - create validation result indicating format error
            return {
                "is_valid": False,
                "strategic_alignment": {"passed": False, "issues": ["Invalid JSON format"]},
                "boundary_compliance": {"passed": False, "issues": ["Cannot validate due to JSON error"]},
                "coordination_check": {"passed": False, "issues": ["Cannot validate due to JSON error"]},
                "architecture_consistency": {"passed": False, "issues": ["Cannot validate due to JSON error"]},
                "overall_score": 0,
                "recommendations": [f"JSON format error: {str(e)}"]
            }
        except Exception as e:
            # Other validation errors
            return {
                "is_valid": False,
                "strategic_alignment": {"passed": False, "issues": [f"Validation error: {str(e)}"]},
                "boundary_compliance": {"passed": False, "issues": ["Validation failed"]},
                "coordination_check": {"passed": False, "issues": ["Validation failed"]},
                "architecture_consistency": {"passed": False, "issues": ["Validation failed"]},
                "overall_score": 0,
                "recommendations": [f"Validation error: {str(e)}"]
            }

    def _process_phase_worker(self, phase_info: Dict[str, Any], worker_id: int) -> Dict[str, Any]:
        """Worker function to process a single phase with strategic context and validation."""
        # Update worker status - starting phase
        phase_desc = f"{phase_info['phase_id']}: {phase_info['title']} ({phase_info['duration']} min)"
        self.worker_monitor.update_worker(worker_id, f"Starting strategic analysis for {phase_desc}", WorkerState.ACTIVE)

        # Build strategic context for validation
        strategic_context = self.phase_manager.build_strategic_context(phase_info['phase_id'])

        # Create enhanced prompt file with strategic context
        prompt_file = self._create_enhanced_prompt_file(phase_info)
        if not prompt_file:
            self.worker_monitor.set_worker_error(worker_id, "Failed to create enhanced prompt file")
            return {
                "success": False,
                "error": "Failed to create enhanced prompt file",
                "phase_id": phase_info['phase_id']
            }

        # Create prompt content for agent manager
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_content = f.read()

        # Call agent manager to process this phase
        try:
            result = self.agent_manager.process_agent_worker(
                "plan-breakdown-analyzer",
                prompt_content,
                worker_id,
                {"phase_info": phase_info},
                strategic_context
            )

            if result["success"]:
                self.worker_monitor.update_worker(worker_id, f"Validating breakdown for {phase_info['phase_id']}", WorkerState.ACTIVE)

                # Validate the breakdown result against strategic context
                validation_result = self._validate_breakdown_result(
                    result.get("response", ""),
                    strategic_context,
                    phase_info['phase_id']
                )

                if validation_result["is_valid"]:
                    self.worker_monitor.set_worker_completed(worker_id, f"Completed {phase_info['phase_id']} (Score: {validation_result['overall_score']})")
                    success = True
                    validation_passed = True
                else:
                    self.worker_monitor.set_worker_error(worker_id, f"Validation failed for {phase_info['phase_id']} (Score: {validation_result['overall_score']})")
                    success = False
                    validation_passed = False
                    error_msg = f"Strategic validation failed: {', '.join(validation_result['recommendations'][:2])}"
            else:
                error_msg = result.get("error", "Unknown error")
                validation_passed = False

        except Exception as e:
            self.worker_monitor.set_worker_error(worker_id, f"Exception: {str(e)}")
            error_msg = f"Exception: {e}"
            validation_passed = False
            success = False

        finally:
            # Clean up prompt file
            try:
                os.remove(prompt_file)
            except Exception:
                pass

        # Return enhanced result with validation
        if success and validation_passed:
            return {
                "success": True,
                "response": result.get("response", ""),
                "phase_id": phase_info['phase_id'],
                "validation": validation_result,
                "strategic_context": strategic_context
            }
        else:
            return {
                "success": False,
                "error": error_msg if 'error_msg' in locals() else result.get("error", "Unknown error"),
                "response": result.get("response", ""),
                "phase_id": phase_info['phase_id'],
                "validation": validation_result if 'validation_result' in locals() else None,
                "strategic_context": strategic_context
            }

    def run_loop(self, max_iterations: int = 50) -> bool:
        """
        Run the main breakdown loop with parallel processing and worker monitoring.

        Args:
            max_iterations: Maximum number of iterations to prevent infinite loops

        Returns:
            True if successful, False otherwise
        """
        self.statistics_tracker.start_timing()

        print(f"Starting Breakdown Loop - Workers: {self.max_workers}, Iterations: {max_iterations}")

        # Start worker monitoring display
        self.worker_monitor.start_display()

        try:
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                # Find phases needing breakdown
                phases_needing_breakdown = self.phase_manager.find_phases_needing_breakdown(limit=50)

                if not phases_needing_breakdown:
                    summary = self.worker_monitor.get_summary()
                    print(f"[OK] No phases need breakdown - all within 60min limit")
                    print(f"Stats: {self.statistics_tracker.successful_items} success, {self.statistics_tracker.failed_items} failed")
                    print(f"Worker Summary: {summary}")
                    print("\n[OK] Breakdown loop completed!")
                    return True

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
                            # Update statistics
                            self.statistics_tracker.update_success(result["success"])

                            # Log detailed results for debugging
                            if result["success"]:
                                validation = result.get("validation", {})
                                print(f"✓ Worker completed: {phase['phase_id']} completed successfully")
                                print(f"  Validation Score: {validation.get('overall_score', 'N/A')}/100")

                                # Log key validation aspects
                                if validation:
                                    for aspect in ["strategic_alignment", "boundary_compliance", "coordination_check", "architecture_consistency"]:
                                        if aspect in validation:
                                            status = "PASS" if validation[aspect]["passed"] else "FAIL"
                                            print(f"  {aspect.replace('_', ' ').title()}: {status}")
                            else:
                                print(f"✗ Worker failed: {phase['phase_id']} failed")
                                if "validation" in result and result["validation"]:
                                    print(f"  Validation Issues: {len(result['validation']['recommendations'])} found")
                                    for rec in result["validation"]["recommendations"][:2]:
                                        print(f"    - {rec}")
                        except Exception as e:
                            self.worker_monitor.set_worker_error(1, f"Worker exception: {e}")
                            self.statistics_tracker.update_success(False)

                print(f"Batch completed: {len(phases_to_process)} phases processed")
                print(f"Stats: {self.statistics_tracker.successful_items} success, {self.statistics_tracker.failed_items} failed")

            else:
                summary = self.worker_monitor.get_summary()
                print(f"\n[OK] Maximum iterations ({max_iterations}) reached")
                print(f"Final stats: {self.statistics_tracker.successful_items} success, {self.statistics_tracker.failed_items} failed")
                print(f"Final Worker Summary: {summary}")
                return False

        except KeyboardInterrupt:
            from ..shared_helpers import handle_keyboard_interrupt
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_keyboard_interrupt(stats_dict, "Breakdown")
            return False
        except Exception as e:
            from ..shared_helpers import handle_fatal_error
            stats_dict = self.statistics_tracker.get_summary_dict()
            handle_fatal_error(e, stats_dict, "Breakdown")
            return False
        finally:
            # Stop worker monitoring display
            self.worker_monitor.stop_display()