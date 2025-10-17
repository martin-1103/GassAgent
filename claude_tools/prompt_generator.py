#!/usr/bin/env python3
"""
Prompt Generator

Shared prompt generation logic for run.py, break.py, and init.py
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class PromptGenerator:
    """Shared prompt generation for different agent types"""

    def __init__(self, prompt_template_dir: Path):
        """
        Initialize prompt generator

        Args:
            prompt_template_dir: Directory containing agent templates
        """
        self.prompt_template_dir = prompt_template_dir

    def load_project_structure(self) -> Dict[str, Any]:
        """
        Load project structure from .ai/structure/structure.md

        Returns:
            Dictionary containing project structure information
        """
        structure_file = Path(".ai/structure/structure.md")

        if not structure_file.exists():
            return {"content": "", "exists": False}

        try:
            with open(structure_file, 'r', encoding='utf-8') as f:
                content = f.read()
                return {
                    "content": content,
                    "exists": True,
                    "file_path": str(structure_file)
                }
        except Exception as e:
            print(f"[WARNING] Failed to load project structure: {e}")
            return {"content": "", "exists": False, "error": str(e)}

    def load_database_schema(self) -> Dict[str, Any]:
        """
        Load database schema from .ai/schema/index.json

        Returns:
            Dictionary containing database schema information
        """
        schema_file = Path(".ai/schema/index.json")

        if not schema_file.exists():
            return {"content": {}, "exists": False}

        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                content = json.load(f)
                return {
                    "content": content,
                    "exists": True,
                    "file_path": str(schema_file)
                }
        except Exception as e:
            print(f"[WARNING] Failed to load database schema: {e}")
            return {"content": {}, "exists": False, "error": str(e)}

    def format_strategic_context(self, strategic_context: Dict[str, Any]) -> str:
        """
        Format strategic context for prompt inclusion

        Args:
            strategic_context: Strategic context dictionary

        Returns:
            Formatted strategic context string
        """
        if not strategic_context:
            return ""

        formatted = []

        # Project Strategic DNA
        dna = strategic_context.get('strategic_dna', {})
        if dna:
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

        # Parent Chain
        parent_chain = strategic_context.get('parent_chain', [])
        if parent_chain:
            formatted.append("\n### PARENT CHAIN (Hierarchy of Goals)")
            for parent in parent_chain:
                level_indicator = "  " * parent.get('level', 0)
                parent_id = parent.get('id', 'unknown')
                if parent_id == 'project':
                    formatted.append(f"{level_indicator}**Level {parent.get('level', 0)}**: @.ai/plan/phases.json - {parent.get('title', 'Unknown')}")
                else:
                    formatted.append(f"{level_indicator}**Level {parent.get('level', 0)}**: @.ai/plan/{parent_id}.json - {parent.get('title', 'Unknown')}")
                formatted.append(f"{level_indicator}  Goal: {parent.get('goal', 'No goal specified')}")

        # Sibling Coordination
        coordination = strategic_context.get('sibling_coordination', {})
        if coordination.get('has_siblings'):
            formatted.append("\n### SIBLING COORDINATION REQUIREMENTS")
            coordination_points = coordination.get('coordination_points', [])
            for point in coordination_points:
                sibling_id = point.get('sibling_id', 'Unknown')
                formatted.append(f"**Sibling @.ai/plan/{sibling_id}.json**: {point.get('sibling_title', 'Unknown')}")
                formatted.append(f"  - Coordination Type: {point.get('coordination_type', 'unknown')}")

        # Boundary Constraints
        constraints = strategic_context.get('boundary_constraints', {})
        if constraints:
            formatted.append("\n### BOUNDARY CONSTRAINTS")

            must_include = constraints.get('must_include', [])
            if must_include:
                formatted.append("**MUST INCLUDE**: " + ", ".join(must_include))

            must_not_include = constraints.get('must_not_include', [])
            if must_not_include:
                formatted.append("**MUST NOT INCLUDE**: " + ", ".join(must_not_include))

            scope_limits = constraints.get('scope_limits', [])
            if scope_limits:
                formatted.append("**SCOPE LIMITS**: " + ", ".join(scope_limits))

        return "\n".join(formatted)

    def format_project_context(self) -> str:
        """
        Format project structure and database schema context

        Returns:
            Formatted project context string
        """
        context_parts = []

        # Load project structure
        project_structure = self.load_project_structure()
        if project_structure.get('exists'):
            context_parts.append(f"""
## PROJECT STRUCTURE CONTEXT
Current implementation patterns and architecture organization:

{project_structure.get('content', '')}
""")
        else:
            context_parts.append("""
## PROJECT STRUCTURE CONTEXT
No project structure file found at .ai/structure/structure.md
""")

        # Load database schema
        database_schema = self.load_database_schema()
        if database_schema.get('exists'):
            schema_content = database_schema.get('content', {})
            schema_json = json.dumps(schema_content, indent=2)
            context_parts.append(f"""
## DATABASE SCHEMA CONTEXT
Current database schema and data models:

```json
{schema_json}
```
""")
        else:
            context_parts.append("""
## DATABASE SCHEMA CONTEXT
No database schema file found at .ai/schema/index.json
""")

        return "\n".join(context_parts)

    def generate_task_analyzer_prompt(self,
                                     agent_template: str,
                                     available_tasks: list[Dict[str, Any]],
                                     strategic_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate prompt for task-analyzer-executor agent

        Args:
            agent_template: Agent template content
            available_tasks: List of available tasks
            strategic_context: Optional strategic context

        Returns:
            Complete prompt for task-analyzer-executor
        """
        # Format strategic context if available
        strategic_context_text = ""
        if strategic_context:
            strategic_context_text = self.format_strategic_context(strategic_context)

        # Format project context
        project_context_text = self.format_project_context()

        # Convert tasks to JSON
        tasks_json = json.dumps(available_tasks, indent=2)

        prompt = f"""You are task-analyzer-executor agent with enhanced strategic context capabilities.

{agent_template}{strategic_context_text}{project_context_text}

## TASK: Analyze available tasks with complete pre-loaded context and create context files

**Available Tasks:**
```json
{tasks_json}
```

**CRITICAL INSTRUCTIONS:**
1. **Use Pre-loaded Context**: All necessary context (strategic context, project structure, database schemas) is provided above. No additional file loading needed.
2. **For Each Task**:
   - Consider its position in the parent hierarchy chain
   - Respect boundary constraints (MUST/MUST_NOT include)
   - Ensure alignment with project vision and architectural principles
   - Address sibling coordination requirements
   - Analyze using provided project structure and database schema context
3. **Create Context Files**: Save to .ai/brain/tasks/[TASK_ID].md with complete strategic context
4. **Update Status**: Change task status to "in-progress" using PhaseManager
5. **Return JSON**: Provide task file paths created

**Output Location:**
Save task context files to: .ai/brain/tasks/

**Remember**: All context is pre-loaded and provided. Focus on expert analysis and planning, not data retrieval. Use the complete project hierarchy and constraints to ensure tasks align with project goals.

Please proceed with task analysis now.
"""
        return prompt

    def generate_task_validator_prompt(self,
                                      agent_template: str,
                                      task_id: str) -> str:
        """
        Generate prompt for task-validator agent

        Args:
            agent_template: Agent template content
            task_id: ID of the task to validate

        Returns:
            Complete prompt for task-validator
        """
        prompt = f"""You are task-validator agent.

{agent_template}

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
        return prompt

    def generate_task_status_updater_prompt(self,
                                           agent_template: str,
                                           task_id: str,
                                           validation_result: str) -> str:
        """
        Generate prompt for task-status-updater agent

        Args:
            agent_template: Agent template content
            task_id: ID of the task
            validation_result: Result from validation

        Returns:
            Complete prompt for task-status-updater
        """
        prompt = f"""You are task-status-updater agent.

{agent_template}

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
        return prompt

    def generate_plan_analyzer_prompt(self,
                                     agent_template: str,
                                     plan_file: Path,
                                     target_folder: Optional[str],
                                     plan_dir: Path) -> str:
        """
        Generate prompt for plan-analyzer agent

        Args:
            agent_template: Agent template content
            plan_file: Path to plan file
            target_folder: Optional target folder name
            plan_dir: Directory to save plan files

        Returns:
            Complete prompt for plan-analyzer
        """
        prompt = f"""You are plan-analyzer agent.

{agent_template}

## TASK: Analyze PRD and generate development phases

**Input Information:**
- Plan File: {plan_file}
- Target Folder: {target_folder or 'Not specified'}

**Instructions:**
1. Read and analyze the plan file: {plan_file}
2. {f'Analyze existing project in: {target_folder}' if target_folder else 'Treat as new project'}
3. Generate comprehensive development phases with dependencies
4. Create index.json and phases.json in {plan_dir}
5. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {plan_dir}/

Please proceed with the analysis now.
"""
        return prompt

    def generate_database_schema_designer_prompt(self,
                                                agent_template: str,
                                                plan_dir: Path,
                                                schema_dir: Path,
                                                target_folder: Optional[str]) -> str:
        """
        Generate prompt for database-schema-designer agent

        Args:
            agent_template: Agent template content
            plan_dir: Directory containing plan files
            schema_dir: Directory to save schema files
            target_folder: Optional target folder name

        Returns:
            Complete prompt for database-schema-designer
        """
        prompt = f"""You are database-schema-designer agent.

{agent_template}

## TASK: Generate phase-aware database schema

**Input Context:**
- Plan analysis available in: {plan_dir}/
- Target Folder: {target_folder or 'Not specified'}

**Instructions:**
1. Read plan analysis from {plan_dir}/index.json and {plan_dir}/phases.json
2. Analyze data requirements based on development phases
3. Design phase-aware database schema
4. Generate schema files in {schema_dir}/
5. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {schema_dir}/

Please proceed with the database schema design now.
"""
        return prompt

    def generate_project_structure_generator_prompt(self,
                                                  agent_template: str,
                                                  plan_dir: Path,
                                                  structure_dir: Path,
                                                  target_folder: Optional[str]) -> str:
        """
        Generate prompt for project-structure-generator agent

        Args:
            agent_template: Agent template content
            plan_dir: Directory containing plan files
            structure_dir: Directory to save structure file
            target_folder: Optional target folder name

        Returns:
            Complete prompt for project-structure-generator
        """
        prompt = f"""You are project-structure-generator agent.

{agent_template}

## TASK: Generate phase-aware project structure

**Input Context:**
- Plan analysis available in: {plan_dir}/
- Target Folder: {target_folder or 'project'}

**Instructions:**
1. Read plan analysis from {plan_dir}/index.json and {plan_dir}/phases.json
2. {f'Scan existing project structure in: {target_folder}' if target_folder else 'Design new project structure'}
3. Design phase-aware directory structure
4. Use "{target_folder or 'project'}" as root directory name
5. Generate structure.md in {structure_dir}/
6. Follow all output format requirements from the agent template

**Output Location:**
Save results to: {structure_dir}/structure.md

Please proceed with the project structure generation now.
"""
        return prompt