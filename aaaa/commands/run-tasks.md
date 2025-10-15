---
description: Get leaf tasks, update status to in-progress, then execute them with Claude in parallel (max 5)
---

## Context References:
Project Structure: @.ai\structure\structure.md
Database Schema: @.ai\schemas\index.json

## Task Analysis & Execution:
Use task-analyzer-executor subagent to get available tasks and create context files

Based on task files created, execute tasks in parallel using:
- **Execution Command**: `cd "D:\MCP\planner2" && .gass/script/run_claude.bat "Dengan konteks lengkap dari file .ai/brain/tasks/[TASK_ID].md, kerjakan task tersebut. Ikuti recommendations dan existing patterns yang sudah dianalisis. Max 300 lines per file dengan AI-friendly naming."`
- **Parallel Limit**: Maximum $1 concurrent tasks (default: 5)
- **Status Management**: Task status updater handles pre-execution in-progress status and post-execution completion based on validation results

## Quality Validation & Status Management:
Use task-validator subagent for quality assessment after task completion

- **Validation Process**: Task validator reads task context, runs lint checking, and creates validation reports
- **Status Management**: Use task-status-updater subagent to update status based on validation results
- **Validation Reports**: Saved to `.ai/brain/validation/[TASK_ID]_report.md`
- **Status Logs**: Saved to `.ai/brain/status/[TASK_ID]_log.md`

## Execution Rules:
- Monitor task progress and show completion summary
- For completed tasks: Run validation first, then update status
- Validation PASS → Update status to completed
- Validation FAIL → Keep status as in-progress (needs revision)
- Validation PARTIAL → Keep status as in-progress (needs improvements)

## Agent Coordination Rules:
- **Task Analysis**: task-analyzer-executor creates context files and handles initial in-progress status
- **Quality Validation**: task-validator manages lint checking, quality assessment, and integration verification
- **Status Management**: task-status-updater handles all status transitions and documentation
- **Documentation**: Validation reports saved to `.ai/brain/validation/[TASK_ID]_report.md`
- **Status Logs**: Status changes logged to `.ai/brain/status/[TASK_ID]_log.md`

