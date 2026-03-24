# LockedInClaude

A completely offline, file-based context memory system for Claude. **Zero dependencies**, **zero internet**, **pure Python stdlib**.

## Why?

You work on projects for weeks, figure out architecture and patterns, then context evaporates. Claude asks "what's the journaler pattern again?" and you're starting over.

**LockedInClaude** stores persistent, queryable memories that:
- Survive session restarts and process crashes
- Work in air-gapped, offline environments  
- Scale to thousands of entries without external packages
- Support team collaboration through memory sharing
- Deduplicate intelligently (exact hash + fuzzy keyword matching)
- Self-heal corrupted indexes on startup

## Features

| Feature | How It Works |
|---------|-------------|
| **Two-tier memory** | Longterm (persistent) + Transient (session-scoped) |
| **Auto-detection** | Reads content, determines if longterm or transient |
| **Keyword search** | Stemmed, stop-word filtered, fuzzy matching |
| **Deduplication** | SHA-256 exact match + Jaccard fuzzy keyword match |
| **Concurrency-safe** | POSIX `fcntl.flock()` prevents corruption across parallel sessions |
| **Self-healing** | Validates index & checksums on startup, auto-repairs |
| **Atomic writes** | Temp file → rename pattern prevents partial writes |
| **Tagging** | #architecture, #decision, #bug, #pattern, #api, etc. |
| **Sharing** | Export single projects or full backup via dump/devour |
| **Merge strategies** | skip, overwrite, or newest (default) for team imports |

## Quick Start

```bash
# Init (creates ~/.locked-in-claude/ structure)
python3 bin/init.py

# Store context (auto-detects memory type)
python3 bin/store.py --project myapp --auto \
  --title "Auth pattern in login handler" \
  --content "Uses journaler base class that..." \
  --keywords "auth,journaler,handler" --tags "#architecture"

# Query later
python3 bin/query.py --project myapp --keywords "auth"

# Summary only (cheap, just id/title/tags)
python3 bin/query.py --project myapp --keywords "auth" --summary

# List all projects
python3 bin/list.py

# Check active session
python3 bin/query.py --project myapp --session

# Export to share
python3 bin/dump.py --project myapp --output ~/myapp_dump.txt
python3 bin/dump.py --all --output ~/full_backup.txt

# Import from teammate
python3 bin/devour.py --file ~/teammate_dump.txt --project myapp --dry-run
python3 bin/devour.py --file ~/teammate_dump.txt --project myapp --merge-strategy newest

# Validate index health
python3 bin/maintain.py --validate

# Rebuild index from scratch
python3 bin/maintain.py --rebuild
```

## Commands

| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `init.py` | System setup & validation | `--force`, `--validate-only` |
| `store.py` | Save memory | `--auto`, `--stdin`, `--type`, `--no-fuzzy-dedup`, `--dry-run` |
| `query.py` | Retrieve memory | `--keywords`, `--tag`, `--session`, `--since`, `--recent`, `--summary`, `--full`, `--limit` |
| `list.py` | Discover projects | `--type`, `--format` |
| `archive.py` | Archive session | `--project` |
| `maintain.py` | Index health | `--validate`, `--rebuild`, `--vacuum`, `--older-than` |
| `migrate.py` | Schema migrations | `--from-version`, `--to-version`, `--dry-run` |
| `dump.py` | Export memories | `--project`, `--all`, `--output`, `--format` |
| `devour.py` | Import memories | `--file`, `--project`, `--merge-strategy` (skip\|overwrite\|newest), `--dry-run` |

## Sharing Workflow

### Single Project
```bash
# Alice exports
python3 bin/dump.py --project shared_patterns --output patterns.txt

# Bob imports (preview first)
python3 bin/devour.py --file patterns.txt --project shared_patterns --dry-run

# Bob commits import
python3 bin/devour.py --file patterns.txt --project shared_patterns --merge-strategy newest
```

### Full Backup (All Projects)
```bash
# Export everything
python3 bin/dump.py --all --output team_backup_2024.txt

# Import everything (restores source project tracking)
python3 bin/devour.py --file team_backup_2024.txt
```

### Merge Strategies
- **skip** — Keep existing entries, ignore imported duplicates
- **overwrite** — Replace all with imported versions
- **newest** — Update only if imported entry is newer (safe default)

## Data Storage

```
~/.locked-in-claude/
├── longterm/
│   ├── index.json                    # Global inverted keyword index
│   └── projects/{project}/memories.json
│
├── transient/
│   └── projects/{project}/
│       ├── session.json              # Active session
│       └── sessions/{id}.json        # Archived sessions
│
└── locks/                            # POSIX file locks
    └── {project}.lock
```

## Requirements

- Python 3.6+ (stdlib only: hashlib, uuid, json, fcntl, datetime)
- **No external packages**
- Works fully offline in air-gapped networks
- RHEL8, Ubuntu, macOS, any POSIX system

## Status Codes

All commands output `STATUS:` prefix:
- `STATUS:OK` — Success
- `STATUS:SKIP` — Skipped (duplicate, already exists)
- `STATUS:WARN` — Succeeded with warnings
- `STATUS:ERROR` — Failed
- `STATUS:DRY` — Dry-run (no changes)

Always check the status before consuming output.

## Documentation

- [PLAN.md](./PLAN.md) — Full technical specification (architecture, algorithms, data structures)
- [CLAUDE.md](./CLAUDE.md) — Integration guide for Claude instances
