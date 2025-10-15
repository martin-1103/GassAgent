# Slash Commands

## Built-in Commands
| Command | Purpose |
|---|---|
| `/add-dir` | Add working directories |
| `/agents` | Manage AI subagents |
| `/clear` | Clear conversation |
| `/config` | Open Settings |
| `/help` | Get help |
| `/memory` | Edit CLAUDE.md |
| `/model` | Select AI model |
| `/status` | Check status |
| `/vim` | Enter vim mode |

## Custom Commands

### Location
- **Project**: `.claude/commands/` (shared)
- **Personal**: `~/.claude/commands/` (private)

### Syntax
```
/<command-name> [arguments]
```

### Arguments
- `$ARGUMENTS` - All arguments
- `$1`, `$2`, etc. - Individual arguments

### Examples

#### Simple command
```bash
echo "Analyze performance: $ARGUMENTS" > .claude/commands/optimize.md
```

#### Positional arguments
```bash
echo "Review PR #$1 with priority $2" > .claude/commands/review-pr.md
```

#### Bash execution
```markdown
---
allowed-tools: Bash(git add:*), Bash(git commit:*)
---
Current git status: !`git status`
Current changes: !`git diff HEAD`

Create commit based on changes above.
```

### Frontmatter Options
```yaml
---
allowed-tools: Bash,Read
argument-hint: [message]
description: Create git commit
model: sonnet
---
```

## MCP Commands
Format: `/mcp__<server>__<prompt> [args]`

## SlashCommand Tool
Claude can execute commands programmatically when referenced by name.