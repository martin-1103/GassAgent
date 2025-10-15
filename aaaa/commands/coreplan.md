---
name: coreplan
description: Generate coreplan from plan file path and analyze with plan-analyzer agent
argument-hint: <plan-file-path>
allowed-tools: Task
---

Generate coreplan from plan file and analyze with plan-analyzer agent.

Usage: /coreplan <path-to-plan-file>

This command will:
1. Call the plan-analyzer agent to analyze the plan at the specified path
2. Generate structured JSON output saved to .ai/plan/ directory

Plan file path provided: $1

!# Use the plan-analyzer agent to analyze the plan file
Task
description</arg_key>
<arg_value>Analyze plan file using plan-analyzer agent