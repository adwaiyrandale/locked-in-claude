# Context Memory

You have access to a local memory system at ~/.locked-in-claude/
ALWAYS check the STATUS: prefix before using any output.

## Retrieve context
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --keywords "term1,term2" --format json

## Retrieve by tag
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --tag "#decision" --full

## Retrieve recent (last 2 hours)
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --since 2h --recent 10

## Retrieve summary only (cheap)
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --keywords "term" --summary

## Store context (auto-detects longterm vs transient)
python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --auto \
  --title "Description" --content "Full context..." \
  --keywords "term1,term2" --tags "#architecture,#decision"

## Check active session
python3 ~/.locked-in-claude/bin/query.py --project <name> --session

## List all projects
python3 ~/.locked-in-claude/bin/list.py

## Export memories (to share with team)
python3 ~/.locked-in-claude/bin/dump.py --project <name>
python3 ~/.locked-in-claude/bin/dump.py --all  # Full backup

## Import/ingest shared memories
python3 ~/.locked-in-claude/bin/devour.py \
  --file /path/to/dump.txt --project <name>

## When to use

ALWAYS query memory when:
- Starting work on a file you have not seen this session
- The user asks about architecture, patterns, or component relationships
- You are about to make a design decision that might contradict prior decisions
- Before importing a memory dump from another user

## Tips

- Use --auto to let the system decide memory type (longterm/transient)
- Use --summary for quick orientation before fetching full content
- Check STATUS:OK, STATUS:SKIP, STATUS:WARN, STATUS:ERROR in all output
- Use dump/devour to share memories with team members
