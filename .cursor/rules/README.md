# Cursor Rules

This directory contains project-wide rules that Cursor applies during coding sessions.

## How to use
- Rules marked with `alwaysApply: true` are enforced automatically across the repo.
- Each rule can target files via `globs`. Adjust globs to scope rules by folder or extension.
- Prefer one focused rule per file for clarity and maintenance.
 - On macOS, commands and examples use POSIX shell (bash/zsh) equivalents.

## Available rules
- `Global-Development-Workflow.md`: universal development workflow (planning → scaffolding → implementation → testing → finalization), including folder standards, soft-deletes, changelog and error logging, checkpoints, and completion criteria.

## Adding new rules
1. Create a new markdown file in this folder.
2. Add a frontmatter block:
   ```
   ---
   description: Short description of what the rule enforces
   globs: ["**/*"]
   alwaysApply: false
   ---
   ```
3. Document the expectations and any exceptions.
4. Keep rules concise and actionable; avoid duplicating content across files.

## DhanHQ-specific rules
DhanHQ v2 integration rules are referenced from `@docs_links.txt`. Use those links as the single source of truth when implementing DhanHQ features (auth, data, orders, market data WS, retries, SQLite usage). Add dedicated rule files here if you want Cursor to enforce broker-specific conventions in this repository.
