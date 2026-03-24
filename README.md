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

## Features

- Two-tier memory (longterm + transient)
- Auto-detect memory type based on content
- Keyword search with stemming
- Fuzzy deduplication (Jaccard similarity)
- File locking for concurrent sessions
- Self-healing index on startup
- Atomic writes (no corrupted files)
- Tags support (#architecture, #decision, #bug)

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

## More

See [PLAN.md](./PLAN.md) for full details.

## Reqs

- Python 3.6+
- No packages needed
- Works fully offline
