---
description: Universal Development Workflow Rules
globs: ["**/*"]
alwaysApply: true
---

# Global Development Workflow Rules

## 1. Core Principles

### Structured Thinking
- Always reason from first principles; break problems into atomic components
- Document the logic (cause → effect) for every step
- Use systematic problem-solving approaches

### Strategic Planning First
- Define goals, constraints, assumptions, and dependencies
- Produce a stepwise plan before executing any code
- Consider multiple approaches before implementation

### Stepwise Execution
- Execute tasks incrementally
- Do not skip steps or checkpoints
- Validate each step before proceeding

### Checkpoint Gating
- Verify and approve work at each checkpoint before proceeding
- Use defined checkpoints to ensure quality and progress
- Do not proceed without checkpoint approval

### Audit & Documentation
- Maintain **changelogs**, **error logs**, and **TODO lists**
- Document all significant changes and decisions
- Keep comprehensive project history

### Soft Deletes Only
- Move deleted/obsolete files to a deleted/ folder with timestamp and manifest
- Never permanently delete files without backup
- Maintain file history for rollback purposes

### Shell Commands (macOS/Linux)
- Prefer POSIX-compliant shell commands (bash/zsh) on macOS
- Use cross-platform commands when possible
- Document command dependencies

### Shell Scripts (macOS/Linux)
- Write scripts in POSIX shell (bash/zsh) for portability
- Use cross-platform commands when possible
- Document command dependencies and required tools

### Readable Over Clever
- Clarity and maintainability take precedence over shortcuts
- Write self-documenting code
- Prioritize team understanding over individual cleverness

## 2. Folder Hierarchy

```
root/
│
├── tasks/                          # Task-specific folders
│   ├── Task-001/
|   |   ├── delete/                  # Task-specific TODO
│   │   ├── src/                     # Source code
│   │   ├── tests/                   # Task-specific tests (non-release)
│   │   ├── changelogs.md            # Task-specific changelog
│   │   ├── errors.md                # Task-specific errors
│   │   └── TODO.md                  # Task-specific TODO
│   │
│   └── Task-002/ …                  # Same structure
│
├── tests/                            # Global tests (integration, regression)
│
├── TODO/                             # Global TODO folder
│   ├── TODO-001.md
│   ├── TODO-002.md
│   └── …
│
├── deleted/                           # Soft-deleted files (including tests)
│
├── changelogs/                        # Optional global changelogs
├── errors/                            # Optional global error logs
```

## 3. Task Workflow

### Planning Phase
1. Create tasks/Task-XXX/TODO.md and tasks/Task-XXX/changelogs.md
2. Define task goal, first-principles breakdown, constraints, and expected outcome
3. Identify dependencies and risks

### Setup Phase
```bash
mkdir -p ./tasks/Task-001/src ./tasks/Task-001/tests
: > ./tasks/Task-001/changelogs.md
: > ./tasks/Task-001/errors.md
: > ./tasks/Task-001/TODO.md
```

### Execution Phase
1. Preview planned changes and PowerShell commands
2. Apply minimal edits, update changelogs, run tests
3. Execute step-by-step with validation

### Testing Phase
1. Run task-specific tests in Task-XXX/tests/
2. Run global tests in tests/
3. Validate all functionality

### Error Handling
1. Document errors in errors.md or global errors/ if cross-task
2. Include symptom, reproduction steps, root cause, fix, prevention
3. Update error logs immediately

### Checkpoint Verification
1. Do not proceed until all tests pass and errors are resolved
2. Update changelogs and TODO status before moving forward
3. Get approval at each checkpoint

## 4. Global TODO Rules

### Location and Structure
- All global tasks live in TODO/
- Each global TODO gets a separate Markdown file
- Use consistent naming: TODO-001.md, TODO-002.md, etc.

### TODO File Format
```markdown
TODO-001: Update Shared Library
****Description:**** Update library X to support feature Y
****Assigned To:**** [Name]
****Status:**** [ ] Pending  [ ] In Progress  [ ] Completed
****Related Tasks:**** Task-005, Task-007
****Priority:**** High/Medium/Low
****Deadline:**** YYYY-MM-DD
```

### Management Rules
1. Update progress and status changes regularly
2. May have checkpoints if impacting multiple tasks or tests
3. Changes related to global TODOs must be logged in changelogs and errors
4. Review and update TODOs weekly

## 5. Tests Management

### Test Organization
- **Task-specific tests:** tasks/Task-XXX/tests/ (non-release)
- **Global tests:** tests/ (integration, regression, shared)
- **Soft-delete:** Obsolete tests moved to deleted/ with timestamped manifest entry

### Test Execution
- Run task-specific tests before global tests
- Ensure all tests pass before proceeding
- Document test results in changelogs

## 6. Changelog Rules

### Documentation Requirements
- Each task folder: changelogs.md
- Log immediately for every change
- Include timestamp, files modified, description, PowerShell commands, test results

### Logging Format
```bash
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo "$timestamp: Updated function X; tests passed" >> ./tasks/Task-001/changelogs.md
```

### Global Changelog
- Global TODO changes affecting multiple tasks should also be logged in changelogs/global.md
- Maintain project-wide change history

## 7. Error Logging Rules

### Error Documentation
Include in every error log:
- Symptom description
- Reproduction steps (PowerShell commands)
- Root cause analysis
- Fix implementation
- Prevention measures

### Logging Format
```bash
echo "ERROR: Missing config; fixed by creating default config" >> ./tasks/Task-001/errors.md
```

### Global Error Management
- Global errors affecting multiple tasks can be logged in errors/global.md
- Track error patterns across tasks

## 8. Soft-Delete Rules

### File Management
- Move deleted or obsolete files to deleted/DATESTAMP/ preserving folder structure
- Never permanently delete without backup

### Implementation
```bash
ts=$(date '+%Y%m%d-%H%M%S')
file="<relative/path/to/file>" # replace with file to delete softly
dest="./deleted/$ts/$file"
mkdir -p "$(dirname "$dest")"
mv -f "$file" "$dest"
```

### Manifest Maintenance
- Maintain deleted/index.json manifest with:
  - originalPath
  - newPath
  - timestamp
  - reason
  - taskId

## 9. Checkpoints

| **Checkpoint**     | **Description**                                        |
|:------------------:|:------------------------------------------------------:|
| CP-1 Plan          | Task strategy, TODO, global test dependencies approved |
| CP-2 Scaffold      | Create folders, files, task tests                      |
| CP-3 Implement     | Code and task-specific tests created                   |
| CP-4 Test & Verify | Task and global tests pass; errors fixed               |
| CP-5 Finalize      | Update changelogs, errors, soft-deletes, TODOs         |

## 10. Task Completion Criteria

### Final Validation
- All checkpoints approved
- Changelogs updated
- Errors documented and fixed
- Deleted files moved to deleted/
- Task and global tests executed successfully
- TODO lists updated

### Quality Gates
- No critical errors unresolved
- All documentation complete
- Code review completed
- Performance requirements met
- Security requirements satisfied

---

*These global rules apply to all projects and ensure consistent, high-quality development practices.*


