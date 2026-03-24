# LockedInClaude

A local file-based context memory system for Claude.

## What

Store project context, patterns, and architecture decisions that persist across Claude sessions. No internet needed, just JSON files.

## Quick

```bash
# Setup
python3 bin/init.py

# Store something
python3 bin/store.py --project myproject --type longterm \
  --title "How auth works" --content "The auth handler..." \
  --keywords "auth,handler,middleware"

# Find it later
python3 bin/query.py --project myproject --keywords "auth"

# See current session
python3 bin/query.py --project myproject --session

# Auto-detect type (let Claude decide)
python3 bin/store.py --project myproject --auto \
  --title "Journaler pattern" --content "The journaler extends..."
```

## Files

- `bin/init.py` - Setup
- `bin/store.py` - Save memories
- `bin/query.py` - Find memories
- `bin/list.py` - List projects
- `bin/archive.py` - Archive sessions
- `bin/maintain.py` - Rebuild/validate index
- `bin/migrate.py` - Schema changes

## More

See [PLAN.md](./PLAN.md) for full details.

## Reqs

- Python 3.6+
- No packages needed
