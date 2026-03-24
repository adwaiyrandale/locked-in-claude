# LockedInClaude

A local file-based context memory system for Claude. Works completely offline with zero dependencies.

## Why

You work on a project for weeks, figure out how things work, then next month you forget. Or you have multiple projects and Claude keeps asking "what's the journaler again?"

This stores project context that persists across Claude sessions. No internet needed. No external packages. Just JSON files in `~/.locked-in-claude/`.

## Use Cases

**Air-gapped environments** - No internet? No problem. Everything stays local.

**Enterprise/closed networks** - Works in secure environments where external packages aren't allowed.

**Multi-project memory** - Store patterns, architecture decisions, component relationships and find them later.

**Session tracking** - Keep track of what you're working on in the current session.

**Sharing** - Export memories to share with team members via email/Confluence/Slack.

## Features

- Two-tier memory (longterm + transient)
- Auto-detect memory type based on content
- Keyword search with stemming
- Fuzzy deduplication (Jaccard similarity)
- File locking for concurrent sessions
- Self-healing index on startup
- Atomic writes (no corrupted files)
- Tags support (#architecture, #decision, #bug)
- Export/import memories (dump/devour)
- Full backup with --all flag

## Quick

```bash
# Setup
python3 bin/init.py

# Store something (auto-detects longterm vs transient)
python3 bin/store.py --project myproject --auto \
  --title "How auth works" --content "The auth handler..." \
  --keywords "auth,handler,middleware"

# Find it later
python3 bin/query.py --project myproject --keywords "auth"

# Cheap summary (id, title, tags only)
python3 bin/query.py --project myproject --keywords "auth" --summary

# See current session
python3 bin/query.py --project myproject --session

# List all projects
python3 bin/list.py

# Export memories (share with team)
python3 bin/dump.py --project myproject
python3 bin/dump.py --all           # Full backup

# Import memories
python3 bin/devour.py --file shared_dump.txt --project myproject

# Validate index
python3 bin/maintain.py --validate
```

## Files

- `bin/init.py` - Setup + self-healing
- `bin/store.py` - Save memories (--auto, --stdin, --no-fuzzy-dedup)
- `bin/query.py` - Find memories (--summary, --limit, --since, --tag)
- `bin/list.py` - List projects
- `bin/archive.py` - Archive sessions
- `bin/maintain.py` - Rebuild/validate/vacuum
- `bin/migrate.py` - Schema changes
- `bin/dump.py` - Export memories (--all for full backup)
- `bin/devour.py` - Import memories

## Sharing Workflow

1. **Export**: `python bin/dump.py --project zap --output ~/shared/zap_dump.txt`
2. **Share**: Send file via email/Confluence/Slack
3. **Import**: `python bin/devour.py --file ~/Downloads/zap_dump.txt --project zap`

Or full backup:
1. **Export all**: `python bin/dump.py --all`
2. **Import all**: `python bin/devour.py --file ALL_memoryDump.txt`

## More

See [PLAN.md](./PLAN.md) for full details including implementation guide.

## Reqs

- Python 3.6+
- No packages needed
- Works fully offline
