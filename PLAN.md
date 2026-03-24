# LockedInClaude

A local file-based context memory system for Claude

---

## Why

Sometimes you work on a project for weeks, figure out how things work, and then next month you forget. Or you have multiple projects and Claude keeps asking "what's the journaler again?"

This is a simple memory system that:
- Stores project context in JSON files
- Works completely offline
- Needs no external packages
- Can be queried while Claude is working

---

## Structure

```
~/.locked-in-claude/
├── longterm/                    # Things that stick around
│   ├── index.json              # Keyword search index
│   └── projects/
│       └── {project}/
│           └── memories.json   # The actual memories
│
├── transient/                  # Current session stuff
│   └── projects/
│       └── {project}/
│           ├── session.json    # Active session
│           └── sessions/       # Old sessions
│
├── locks/                      # Lock files
├── migrations/                 # Schema changes
└── bin/
    ├── init.py
    ├── store.py
    ├── query.py
    ├── archive.py
    ├── list.py
    ├── maintain.py
    └── migrate.py
```

---

## Memory Types

### Longterm
Project stuff that matters forever - architecture decisions, patterns, how components relate.

```json
{
  "id": "uuid",
  "type": "pattern",
  "title": "Journaler Pattern",
  "content": "The journaler is the base class...",
  "keywords": ["journaler", "pattern", "base-class"],
  "tags": ["#decision", "#architecture"],
  "related_entries": ["other-uuid"],
  "created_at": "2024-01-15T10:30:00Z"
}
```

Types: context, architecture, pattern, relationship, note, decision

### Transient
Current session stuff - what you're working on, recent files edited.

```json
{
  "session_id": "uuid",
  "session_start": "2024-01-15T10:30:00Z",
  "active_tasks": [
    {"id": "task-1", "description": "Fix bug", "status": "in_progress", "priority": "high"}
  ],
  "recent_context": [
    {"type": "file_edit", "path": "src/main.go", "summary": "Changed handler"}
  ],
  "session_notes": "Working on auth refactor"
}
```

Task statuses: pending, in_progress, completed, blocked, cancelled

---

## Index

We keep a global index for fast keyword search:

```json
{
  "type": "longterm",
  "entries": [
    {"project": "zap", "file": "projects/zap/memories.json", "keywords": ["journaler", "auth"]}
  ],
  "keyword_index": {
    "journaler": [{"project": "zap", "file": "projects/zap/memories.json"}]
  }
}
```

Each index entry also has a checksum so we can detect when files change.

---

## CLI

### init.py
```bash
python3 bin/init.py              # Setup
python3 bin/init.py --force      # Re-setup
```

### store.py
```bash
# Longterm memory
python3 bin/store.py --project zap --type longterm \
  --title "Journaler Pattern" --content "The journaler is..." \
  --keywords "journaler,pattern" --tags "#decision"

# Transient task
python3 bin/store.py --project zap --type transient \
  --task "Fix login bug" --status in_progress --priority high
```

### query.py
```bash
# By project
python3 bin/query.py --project zap

# By keywords
python3 bin/query.py --project zap --keywords "journaler"

# By tag
python3 bin/query.py --project zap --tag "#decision"

# Recent
python3 bin/query.py --project zap --recent 5

# Session
python3 bin/query.py --project zap --session

# Since (hours)
python3 bin/query.py --project zap --since 2h

# Output format
python3 bin/query.py --project zap --format json
```

### list.py
```bash
python3 bin/list.py              # List all projects
python3 bin/list.py --format json
```

### maintain.py
```bash
python3 bin/maintain.py --rebuild     # Rebuild index
python3 bin/maintain.py --validate    # Check index health
python3 bin/maintain.py --vacuum --older-than 30  # Clean old sessions
```

### migrate.py
```bash
python3 bin/migrate.py --from-version 1.0 --to-version 2.0
```

---

## Keyword Processing

We process keywords to make search work better:

1. **Lowercase** - "Journaler" -> "journaler"
2. **Stop words** - Remove "the", "and", "is", etc
3. **Stemming** - "authentication" -> "auth", "logging" -> "log"

Built-in stem map (no external deps):

```python
STEM_MAP = {
    "authentication": "auth",
    "journaling": "journal",
    "logging": "log",
    "implementation": "impl",
    # ...
}
```

Auto-extract keywords from content based on word frequency.

---

## Deduplication

Two levels:

1. **Exact** - SHA-256 hash of content. If same hash exists, skip.
2. **Fuzzy** - Jaccard similarity on keywords. If >85% similar, skip.

```python
new_kws = set(normalize_keywords(keywords))
existing_kws = set(existing["keywords"])
jaccard = len(new_kws & existing_kws) / len(new_kws | existing_kws)
if jaccard > 0.85:
    skip()
```

---

## Locking

File locking to prevent corruption when multiple Claude sessions work on same project:

```python
import fcntl

with open(lock_file, 'w') as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    # do stuff
    fcntl.flock(f, fcntl.LOCK_UN)
```

Windows fallback uses lock file spin-wait.

---

## Output

Every command outputs a STATUS line first:

```
STATUS:OK id=abc123 longterm=3
STATUS:SKIP duplicate
STATUS:WARN keywords truncated to 20
STATUS:ERROR code=E003 msg=invalid json
STATUS:DRY would store 1 entry
```

Claude should check STATUS: before parsing rest of output.

---

## Errors

| Code | Meaning |
|------|---------|
| E001 | Project not found |
| E002 | Duplicate content |
| E003 | Corrupted JSON |
| E004 | File not found |
| E005 | Permission denied |
| E006 | Lock timeout |
| E007 | Schema mismatch |

---

## Self-Healing

On startup, init.py runs validate() which:
- Checks if indexed files still exist
- Compares checksums to detect changes
- Removes stale entries
- Re-indexes modified files

---

## Claude Integration

Add to your CLAUDE.md or system prompt:

```
## Context Memory

You have access to a local memory system at ~/.locked-in-claude/

### Retrieve context
python3 ~/.locked-in-claude/bin/query.py --project <name> --keywords "term1,term2"

### Store context
python3 ~/.locked-in-claude/bin/store.py --project <name> --type longterm \
  --title "Description" --content "Full context..." \
  --keywords "term1,term2" --tags "#tag"

### Check session
python3 ~/.locked-in-claude/bin/query.py --project <name> --session

### List projects
python3 ~/.locked-in-claude/bin/list.py
```

Query memory when:
- Starting work on a new file
- User asks about architecture or patterns
- About to make a design decision

---

## Performance

| Operation | Time |
|-----------|------|
| Query by project | <5ms |
| Query by keyword | <20ms |
| Query fuzzy | <50ms |
| Store entry | <30ms |
| Full rebuild | <6s |
| Startup validate | <100ms |

Limits:
- 1MB per entry content
- 20 keywords per entry
- 200 chars title
- 10 tags per entry

---

## Security

- Everything local, no network
- File permissions 600
- Don't store secrets/credentials
- Every entry has timestamps

---

## Implementation

Phase 1 - Foundation
- [ ] Directory structure + init.py
- [ ] FileLock class

Phase 2 - Storage
- [ ] normalize_keywords() with stemming
- [ ] store.py with dedup
- [ ] Auto-related entries
- [ ] Incremental index update

Phase 3 - Retrieval
- [ ] query.py with fuzzy search
- [ ] --since, --tag, --full flags
- [ ] Direct file read for transient

Phase 4 - Tools
- [ ] archive.py
- [ ] list.py
- [ ] migrate.py

Phase 5 - Polish
- [ ] maintain.py --rebuild, --validate, --vacuum
- [ ] Checksums in index
- [ ] STATUS: output on all commands

Phase 6 - Test
- [ ] Concurrent writes
- [ ] Corrupted file recovery
- [ ] Migration from old format
- [ ] Query latency

---

## Quick Reference

```bash
# Setup
python3 bin/init.py

# Store
python3 bin/store.py --project zap --type longterm \
  --title "Journaler" --content "The journaler..." \
  --keywords "journaler,pattern"

# Query
python3 bin/query.py --project zap --keywords "journaler"

# List
python3 bin/list.py

# Validate
python3 bin/maintain.py --validate
```

---

*Just JSON files and Python stdlib*
