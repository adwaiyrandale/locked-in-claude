# LockedInClaude Quick Start (5 minutes)

Get up and running in 4 commands.

## Step 1: Initialize (30 seconds)

```bash
python3 bin/init.py
```

Output:
```
STATUS:OK init complete
STATUS:OK validate complete. healed=0
```

## Step 2: Store Your First Memory (1 minute)

```bash
python3 bin/store.py --project myapp --auto \
  --title "How our auth works" \
  --content "We use OAuth2 with JWT tokens. Refresh tokens stored in Redis." \
  --keywords "auth,oauth,jwt"
```

Output:
```
STATUS:OK id=abc123def456...
```

## Step 3: Query It Back (1 minute)

```bash
python3 bin/query.py --project myapp --keywords "auth" --summary
```

Output:
```
STATUS:OK longterm=1 transient=0

--- LONGTERM ---
[1] How our auth works
```

## Step 4: Store a Task (1 minute)

```bash
python3 bin/store.py --project myapp --auto \
  --title "Fix auth bug" \
  --content "Currently debugging token expiry issues in login flow"
```

Output:
```
STATUS:OK id=task-abc123...
```

Check your session:
```bash
python3 bin/query.py --project myapp --session
```

---

## You're Done

You now have:
- ✅ Persistent memory (`~/.locked-in-claude/`)
- ✅ 1 architecture decision stored
- ✅ 1 task tracked
- ✅ Full query capability

## Next Steps

**Share with teammate:**
```bash
python3 bin/dump.py --project myapp --output myapp_memory.txt
# Send myapp_memory.txt via email/Slack

# Teammate imports:
python3 bin/devour.py --file myapp_memory.txt --project myapp
```

**See all projects:**
```bash
python3 bin/list.py
```

**Full docs:**
- `README.md` - Features & workflows
- `CLAUDE.md` - All commands with examples
- `PLAN.md` - Complete technical spec

---

That's it. You're using LockedInClaude. 🚀
