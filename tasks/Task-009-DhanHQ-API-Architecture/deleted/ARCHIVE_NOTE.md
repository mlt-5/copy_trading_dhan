# Archive Note

## Purpose

This directory is reserved for archiving old code and files that are replaced during the migration to the new DhanHQ API-aligned architecture.

---

## What Gets Archived

Files and code from the old `Task-001-Copy-Trading-Architecture` that have been:
- Replaced by new modules in Task-009
- Refactored and restructured
- Superseded by better implementations

---

## Archive Structure

When archiving, use this structure:
```
deleted/
└── YYYYMMDD-HHMMSS/
    ├── manifest.json          # What was archived and why
    ├── old_file1.py
    ├── old_file2.py
    └── ...
```

---

## Manifest Format

Each archive should include a `manifest.json`:

```json
{
  "archive_date": "2025-10-03T22:00:00Z",
  "reason": "Migration to Task-009 architecture",
  "files": [
    {
      "original_path": "tasks/Task-001/src/orders/order_manager.py",
      "archived_path": "deleted/20251003-220000/order_manager.py",
      "replaced_by": "src/core/order_replicator.py",
      "notes": "Refactored with better separation of concerns"
    }
  ]
}
```

---

## Current Status

**As of October 3, 2025 14:42:30**:

✅ **Archive Created**: Task-001 old architecture successfully archived

**Archive Details**:
- **Archive ID**: 20251003-144230
- **Files Archived**: 21 files (18 Python + 2 SQL + 1 main)
- **Archive Size**: 204 KB
- **Source**: tasks/Task-001-Copy-Trading-Architecture/src/
- **Manifest**: deleted/20251003-144230/MANIFEST.md

**Archived Modules**:
- auth/ (authentication)
- config/ (configuration)  
- database/ (database manager, models, schemas)
- errors/ (error handling)
- orders/ (order manager)
- position_sizing/ (position sizer)
- utils/ (logger)
- websocket/ (WebSocket manager)
- main.py (old orchestrator - 11 KB)

---

## Retention Policy

**Suggested**:
- Keep archives for 90 days minimum
- Keep permanent backup of last known good version
- Can safely delete archives after successful production run

---

## Retrieval

To retrieve archived code:

```bash
# List archives
ls -la deleted/

# View manifest
cat deleted/20251003-220000/manifest.json

# Restore file
cp deleted/20251003-220000/file.py ./src/
```

---

## Notes

- This is a **soft delete** system - nothing is permanently lost
- Archives are for reference and rollback safety
- New Task-009 system is production-ready without needing archived code
- Old Task-001 code remains in its original location for reference

