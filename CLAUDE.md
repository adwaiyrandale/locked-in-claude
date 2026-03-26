# Context Memory

You have access to a local memory system at `~/.locked-in-claude/`. Works completely offline with zero external dependencies.

**IMPORTANT**: Always check the `STATUS:` prefix before using any output. Valid statuses:
- `STATUS:OK` — Operation succeeded
- `STATUS:SKIP` — Entry was skipped (duplicate, already exists, etc.)
- `STATUS:WARN` — Operation succeeded with warnings
- `STATUS:ERROR` — Operation failed
- `STATUS:DRY` — Dry-run preview (no changes made)

## Critical Rules for Memory Operations

**When importing memories from teammates (devour.py):**
1. **ALWAYS use `--dry-run` first** to preview what will happen
2. **Use `--merge-strategy newest` (default)** to preserve newer entries from either side
3. **Never use `--merge-strategy overwrite`** unless explicitly told to replace all entries
4. **Check STATUS:WARN** for skipped entries — they indicate duplicates or missing source project

This prevents accidentally overwriting a teammate's newer memories on import.

## Quick Reference

### Store memories
```bash
# Auto-detect type (longterm vs transient)
python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --auto \
  --title "Description" --content "Full context..." \
  --keywords "term1,term2" --tags "#architecture,#decision"

# Store from stdin
cat report.txt | python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --auto --stdin --title "Report"

# Explicit type with fuzzy dedup disabled
python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --type longterm \
  --title "Title" --content "..." --keywords "..." --no-fuzzy-dedup

# Preview without saving
python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --auto --title "Title" --content "..." --dry-run
```

### Query memories
```bash
# Search by keywords
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --keywords "term1,term2" --format json

# Search by tag
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --tag "#decision" --full

# Recent entries (last 2 hours, limit 10)
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --since 2h --recent 10

# Summary only (id, title, tags — cheaper than full)
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --keywords "term" --summary

# Active session tasks
python3 ~/.locked-in-claude/bin/query.py --project <name> --session
```

### Projects & Maintenance
```bash
# List all projects
python3 ~/.locked-in-claude/bin/list.py

# Validate and self-heal index
python3 ~/.locked-in-claude/bin/maintain.py --validate

# Full reindex
python3 ~/.locked-in-claude/bin/maintain.py --rebuild

# Clean up old archived sessions
python3 ~/.locked-in-claude/bin/maintain.py --vacuum --older-than 30d
```

### Export & Import (Sharing with Team)
```bash
# Export single project
python3 ~/.locked-in-claude/bin/dump.py --project <name> --output file.txt

# Export all projects (full backup)
python3 ~/.locked-in-claude/bin/dump.py --all --output ALL_backup.txt

# Preview import without making changes
python3 ~/.locked-in-claude/bin/devour.py \
  --file /path/to/dump.txt --project <name> --dry-run

# Import with merge strategies
# "skip" = keep existing entries (default: "newest")
python3 ~/.locked-in-claude/bin/devour.py \
  --file /path/to/dump.txt --project <name> --merge-strategy skip

# "overwrite" = replace all with imported versions
python3 ~/.locked-in-claude/bin/devour.py \
  --file /path/to/dump.txt --project <name> --merge-strategy overwrite

# "newest" = update if imported is newer (default)
python3 ~/.locked-in-claude/bin/devour.py \
  --file /path/to/dump.txt --project <name> --merge-strategy newest

# Import ALL dump (restores all projects with source tracking)
python3 ~/.locked-in-claude/bin/devour.py --file ALL_backup.txt
```

## When to Use

**ALWAYS query memory when:**
- Starting work on a file you have not seen this session
- The user asks about architecture, patterns, or component relationships
- You are about to make a design decision that might contradict prior decisions
- Before importing a memory dump from another user

**Query FIRST, then act** — this prevents conflicting decisions and duplicates.

## Tips & Best Practices

- Use `--auto` to let the system decide memory type (longterm vs transient)
- Use `--summary` for quick orientation before fetching full content
- Use `--dry-run` to preview imports before committing
- Use `--merge-strategy newest` (default) for safe merges across team members
- Use `--no-fuzzy-dedup` only if you know duplicates are acceptable
- Tags should be consistent across team: `#architecture`, `#decision`, `#bug`, `#pattern`
- Keywords are auto-normalized: stemming + stop-word removal is automatic
- Both exact (SHA-256) and fuzzy (Jaccard) deduplication prevent duplicates
