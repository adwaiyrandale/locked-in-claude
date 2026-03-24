# LockedInClaude: A Local File-Based Context Memory System for Claude
---
## 1. Summary
LockedInClaude is a completely offline, file-based context memory system engineered for Claude Code sessions operating in air-gapped and enterprise environments without internet connectivity. It provides a two-tier persistent memory architecture using only Python standard library primitives and JSON files — zero external dependencies, zero network exposure.
**Design Philosophy:**
Memory as a first-class engineering concern — provides queryable, indexed, deduplicated, and corruption-resilient memory that persists across sessions, survives process restarts, and scales to thousands of entries without performance degradation.
**Key Goals:**
- Zero internet dependency — operates fully in air-gapped environments
- No external packages — pure Python standard library (hashlib, uuid, json, fcntl)
- Efficient keyword-based retrieval with inverted index — O(1) keyword lookup
- Intelligent deduplication — SHA-256 content hashing plus fuzzy Jaccard similarity
- Concurrency-safe — POSIX file locking prevents corruption across parallel sessions
- Self-healing — index validation and automatic repair on startup
- Semantic tolerance — stemming and synonym expansion for improved recall
---
## 2. Architecture Overview
### 2.1 Two-Tier Memory Model
The system is organized into two distinct memory tiers, each optimized for its access pattern and retention requirements:
| **Tier** | **Directory** | **Retention** | **Write Policy** | **Index** |
|----------|---------------|----------------|------------------|-----------|
| Longterm | `~/.locked-in-claude/longterm/` | Permanent | Append-only, no mutations | Global inverted index |
| Transient | `~/.locked-in-claude/transient/` | Session-scoped | Overwrite active session | Session-scoped index only |
### 2.2 Directory Layout
```
~/.locked-in-claude/
├── longterm/                          # Tier 1: Persistent Memory
│   ├── index.json                     # Global inverted keyword index
│   └── projects/
│       └── {project_name}/
│           └── memories.json          # Append-only memory store
│
├── transient/                         # Tier 2: Session Memory
│   └── projects/
│       └── {project_name}/
│           ├── session.json           # Active session (lock-protected)
│           └── sessions/              # Archived past sessions
│               └── {session_id}.json
│
├── locks/                             # Lock files for fcntl
│   └── {project}.lock
│
├── migrations/                       # Schema migration scripts
│   └── v1_to_v2.py
│
└── bin/
    ├── init.py                       # System initialization + validation
    ├── store.py                      # Memory storage (with locking)
    ├── query.py                      # Memory retrieval + fuzzy search
    ├── archive.py                    # Session archival
    ├── list.py                       # Project discovery
    ├── maintain.py                   # Index rebuild, validate, vacuum
    └── migrate.py                    # Schema migration runner
```
### 2.3 Design Principles
| **Principle** | **Implementation** |
|---------------|-------------------|
| Append-Only Longterm | memories.json entries are never modified or deleted after creation |
| Lazy Index on Read | Indexes are updated at write time; reads always use current index |
| Content Hashing | SHA-256 + Jaccard on keywords prevents exact and near-duplicate entries |
| Keyword Normalization | All keywords lowercased, stop-words stripped, suffixes stemmed |
| Concurrency Safety | fcntl.flock(LOCK_EX) on every write; LOCK_SH on reads crossing index |
| Self-Healing Indexes | startup validate() checksums files and removes dead index entries |
| Schema Versioning | Every JSON file carries "schema_version"; migrations run automatically |
---
## 3. Data Structures
### 3.1 Longterm Memory Entry
**File**: `longterm/projects/{project}/memories.json`
```json
{
  "schema_version": "2.0",
  "project": "zap",
  "created_at": "2024-01-15T10:30:00Z",
  "last_updated": "2024-01-15T10:30:00Z",
  "entries": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "type": "pattern",
      "category": "architecture",
      "title": "Journaler Pattern Implementation",
      "content": "The journaler is the base class that provides logging...",
      "keywords": ["journaler", "base-class", "logging", "pattern"],
      "tags": ["#architecture", "#decision"],
      "related_entries": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"],
      "content_hash": "sha256:abc123...",
      "keyword_fingerprint": "base64-of-sorted-kw-set",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```
**Field Definitions:**
| **Field** | **Type** | **Description** |
|-----------|----------|-----------------|
| `id` | UUID v4 | Unique entry identifier |
| `type` | enum | context, architecture, pattern, relationship, note, decision |
| `category` | string | Sub-type for filtering (max 50 chars) |
| `title` | string | Brief description (max 200 chars) |
| `content` | string | Full memory content (max 1MB, truncated with warning) |
| `keywords` | array | Searchable terms — lowercase, stop-word filtered, stemmed (max 20) |
| `tags` | array | Intent tags e.g. #bug, #decision, #api (separate from keywords) |
| `related_entries` | array | UUIDs auto-populated by post-write keyword overlap pass |
| `content_hash` | string | SHA-256 of content for exact dedup |
| `keyword_fingerprint` | string | Base64 of sorted keyword set for Jaccard dedup |
| `schema_version` | string | Schema version for migration runner |
| `created_at` | ISO8601 | Creation timestamp |
| `updated_at` | ISO8601 | Last modification |
### 3.2 Transient Session Entry
**File**: `transient/projects/{project}/session.json`
```json
{
  "schema_version": "2.0",
  "project": "zap",
  "session_id": "sess-a1b2c3d4-e5f6",
  "session_start": "2024-01-15T10:30:00Z",
  "session_end": null,
  "is_active": true,
  "active_tasks": [
    {
      "id": "task-001",
      "description": "Fix authentication bug in login handler",
      "status": "in_progress",
      "priority": "high",
      "tags": ["#bug", "#auth"],
      "created_at": "2024-01-15T10:35:00Z"
    }
  ],
  "recent_context": [
    {
      "type": "file_edit",
      "path": "src/auth/login.go",
      "action": "modified",
      "summary": "Added token refresh logic",
      "timestamp": "2024-01-15T11:00:00Z"
    }
  ],
  "session_notes": "Auth refactor — journaler extends correctly",
  "referenced_memories": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
}
```
**Task Status Values:**
- `pending`, `in_progress`, `completed`, `blocked`, `cancelled`
**Task Priority Values:**
- `low`, `medium`, `high`, `critical`
### 3.3 Global Longterm Index
The longterm global index uses an inverted keyword map for O(1) lookup. The transient index from v1.0 has been **removed** in v2.0 — transient data is always accessed directly by project name; cross-session keyword search on transient data had low utility and high staleness risk.
```json
{
  "schema_version": "2.0",
  "type": "longterm",
  "last_full_reindex": "2024-01-15T10:30:00Z",
  "entries": [
    {
      "project": "zap",
      "file": "projects/zap/memories.json",
      "keywords": ["journaler", "confirmation", "event", "auth"],
      "entry_count": 15,
      "checksum": "sha256:file-level-hash",
      "total_size_bytes": 45678,
      "last_updated": "2024-01-15T10:30:00Z"
    }
  ],
  "keyword_index": {
    "journaler": [{"project": "zap", "file": "projects/zap/memories.json", "entry_ids": ["id1","id2"]}],
    "auth": [{"project": "zap", "file": "...", "entry_ids": ["id3"]}]
  }
}
```
**v2.0 Index Addition: File-Level Checksum**
Each index entry now stores a SHA-256 checksum of the memories.json file. The validate() routine on startup compares stored checksums to actual file hashes. Mismatches trigger automatic removal of the stale index entry and re-indexing of that project only — no full rebuild required.
---
## 4. CLI Interface
### 4.1 Command Reference
| **Command** | **Purpose** | **Key Flags** |
|-------------|-------------|---------------|
| bin/init.py | Initialize or validate system | `--force`, `--validate-only` |
| bin/store.py | Store longterm or transient memory | `--project`, `--type`, `--title`, `--content`, `--keywords`, `--tags`, `--category`, `--dry-run` |
| bin/query.py | Retrieve memories | `--project`, `--keywords`, `--type`, `--recent`, `--since`, `--tag`, `--session`, `--full`, `--format`, `--dry-run` |
| bin/archive.py | Archive current session | `--project` |
| bin/list.py | Discover all projects | `--type`, `--format` |
| bin/maintain.py | Index rebuild, validate, vacuum | `--rebuild`, `--validate`, `--vacuum`, `--older-than` |
| bin/migrate.py | Run schema migrations | `--from-version`, `--to-version`, `--dry-run` |
### 4.2 init.py — Initialization & Startup Validation
On every invocation, init.py runs a lightweight validate() pass before returning. This is the self-healing entry point.
```python
def init(force=False, validate_only=False):
    base_dir = os.path.expanduser("~/.locked-in-claude/")
    
    if validate_only:
        return validate_and_heal(base_dir)
    
    if os.path.exists(base_dir) and not force:
        return validate_and_heal(base_dir)
    
    # Create directories
    for subdir in ["longterm/projects", "transient/projects", "locks", "migrations"]:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
    
    # Create index files
    write_json(os.path.join(base_dir, "longterm/index.json"), {
        "schema_version": "2.0",
        "type": "longterm",
        "last_full_reindex": now(),
        "entries": [],
        "keyword_index": {}
    })
    
    print("STATUS:OK init complete")
    return validate_and_heal(base_dir)
def validate_and_heal(base_dir):
    index_path = os.path.join(base_dir, "longterm/index.json")
    index = read_json(index_path)
    
    # Run schema migration if needed
    if index.get("schema_version") != CURRENT_VERSION:
        run_migration(index["schema_version"], CURRENT_VERSION)
    
    stale = []
    
    for entry in index["entries"]:
        actual_file = os.path.join(base_dir, "longterm", entry["file"])
        
        if not os.path.exists(actual_file):
            stale.append(entry)  # File deleted externally
            continue
        
        actual_checksum = sha256_file(actual_file)
        if actual_checksum != entry.get("checksum"):
            reindex_project(entry["project"])  # File changed — partial reindex
    
    for entry in stale:
        index["entries"].remove(entry)
        remove_from_keyword_index(index, entry["project"])
    
    write_json(index_path, index)
    print(f"STATUS:OK validate complete. healed={len(stale)}")
    return True
```
### 4.3 store.py — Storage with Locking & Deduplication
```python
def store_longterm(project, title, content, keywords, category, tags=[]):
    lock_file = os.path.join(base_dir, "locks", f"{project}.lock")
    
    with exclusive_lock(lock_file):  # fcntl.flock(LOCK_EX)
        data = load_or_create_memories(project)
        
        # Step 1: Exact dedup via SHA-256
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        if content_hash in {e["content_hash"].replace("sha256:", "") for e in data["entries"]}:
            print("STATUS:SKIP duplicate content hash")
            return None
        
        # Step 2: Fuzzy dedup via Jaccard on keywords
        new_kws = set(normalize_keywords(keywords))
        for existing in data["entries"]:
            existing_kws = set(existing["keywords"])
            jaccard = len(new_kws & existing_kws) / len(new_kws | existing_kws)
            if jaccard > 0.85:  # Configurable threshold
                print(f"STATUS:SKIP near-duplicate (Jaccard={jaccard:.2f})")
                return None
        
        # Step 3: Build entry
        cleaned_kws = normalize_keywords(keywords + extract_keywords(content))
        entry = {
            "id": str(uuid.uuid4()),
            "type": category,
            "title": title,
            "content": truncate(content, 1_000_000),
            "keywords": cleaned_kws[:20],
            "tags": [t.lower() for t in tags if t.startswith("#")],
            "related_entries": [],
            "content_hash": f"sha256:{content_hash}",
            "keyword_fingerprint": base64.b64encode(",".join(sorted(cleaned_kws)).encode()).decode(),
            "created_at": now()
        }
        
        # Step 4: Auto-populate related_entries
        entry["related_entries"] = find_related(data["entries"], cleaned_kws, threshold=0.3)
        
        data["entries"].append(entry)
        data["last_updated"] = now()
        
        write_json(memories_file, data)
        update_index_incremental(project, entry)
        
        print(f"STATUS:OK id={entry['id']}")
        return entry["id"]
```
### 4.4 query.py — Retrieval with Fuzzy Matching
```python
def query(project=None, keywords=[], type="both", recent=0, since=None, tag=None, session=False, full=False):
    results = {"longterm": [], "transient": []}
    
    if type in ["longterm", "both"]:
        index = read_json(os.path.join(base_dir, "longterm/index.json"))
        matched = fuzzy_keyword_search(index, project, keywords)
        results["longterm"] = load_and_filter(matched, keywords, since, tag, full)
    
    if type in ["transient", "both"]:
        if session:
            results["transient"] = [get_active_session(project)]
        else:
            # Direct file read — no transient index
            results["transient"] = load_transient_direct(project)
    
    if recent > 0:
        for tier in results:
            results[tier] = sort_by_time(results[tier])[:recent]
    
    print(f"STATUS:OK longterm={len(results['longterm'])} transient={len(results['transient'])}")
    return results
def fuzzy_keyword_search(index, project, keywords):
    if not keywords:
        return get_project_files(index, project)
    
    normalized = [stem(kw.lower()) for kw in keywords]
    candidates = {}
    
    for kw in normalized:
        # Exact match (score +2)
        for match in index.get("keyword_index", {}).get(kw, []):
            file_path = match["file"]
            candidates[file_path] = candidates.get(file_path, 0) + 2
        
        # Stem match (score +1)
        for indexed_kw, matches in index.get("keyword_index", {}).items():
            if stem(indexed_kw) == kw and indexed_kw != kw:
                for match in matches:
                    file_path = match["file"]
                    candidates[file_path] = candidates.get(file_path, 0) + 1
    
    return sorted(candidates.keys(), key=lambda f: candidates[f], reverse=True)
```
### 4.5 New Commands in v2.0
**bin/list.py — Project Discovery:**
```bash
python bin/list.py --type longterm --format text
# Output:
# STATUS:OK count=3
# zap entries=42 last_updated=2024-01-15T10:30:00Z
# api-gateway entries=18 last_updated=2024-01-14T09:00:00Z
# payments entries=7 last_updated=2024-01-10T14:22:00Z
```
**bin/migrate.py — Schema Migration:**
```python
def run_migration(from_ver, to_ver, dry_run=False):
    migration_map = {("1.0", "2.0"): migrate_v1_to_v2}
    fn = migration_map.get((from_ver, to_ver))
    
    if not fn:
        raise MigrationError(f"No path from {from_ver} to {to_ver}")
    
    if dry_run:
        print(f"DRY RUN: would apply migration {from_ver} -> {to_ver}")
        return
    
    fn()
    print(f"STATUS:OK migrated from {from_ver} to {to_ver}")
```
---
## 5. Keyword Processing Pipeline
Keyword quality is the single biggest determinant of retrieval accuracy. v2.0 introduces a multi-stage normalization pipeline.
| **Stage** | **Operation** | **Example** |
|-----------|---------------|-------------|
| 1. Lowercase | Convert to lowercase | "Journaler" → "journaler" |
| 2. Stop-word filter | Remove common English words | "the", "and", "is", "a" removed |
| 3. Suffix stemming | Strip common suffixes | "authentication" → "auth", "logging" → "log" |
| 4. Deduplication | Remove duplicate terms after stemming | ["auth", "authentication"] → ["auth"] |
| 5. Max 20 cap | Truncate with warning if exceeded | Warn user; keep first 20 by TF-IDF score |
### 5.1 Stem Table (Built-In, No External Deps)
```python
STEM_MAP = {
    # Auth domain
    "authentication": "auth", "authorization": "authz",
    "authenticated": "auth", "authorized": "authz",
    
    # Patterns
    "journaling": "journal", "journaler": "journal",
    "logging": "log", "logger": "log",
    
    # Common suffixes
    "implementation": "impl", "implementing": "impl",
    "configuration": "config", "configuring": "config",
    "initialization": "init", "initializing": "init",
    
    # Plurals (simple)
    "handlers": "handler", "services": "service",
    "clients": "client", "servers": "server",
}
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at",
    "to", "for", "of", "with", "by", "from", "is", "are",
    "was", "were", "be", "been", "have", "has", "do", "does"
}
def normalize_keywords(keywords):
    """Multi-stage keyword normalization."""
    result = []
    for kw in keywords:
        kw = kw.lower().strip()
        
        # Remove stop words
        if kw in STOP_WORDS:
            continue
        
        # Apply stemming
        for suffix in ["ing", "ed", "er", "s", "tion", "ly"]:
            if kw.endswith(suffix) and len(kw) > 4:
                stemmed = STEM_MAP.get(kw, kw[:-len(suffix)])
                kw = STEM_MAP.get(stemmed, stemmed)
                break
        
        kw = STEM_MAP.get(kw, kw)
        if kw and kw not in result:
            result.append(kw)
    
    return result[:20]  # Max 20
```
### 5.2 Auto-Keyword Extraction from Content
```python
def extract_keywords(content, max_keywords=10):
    """Extract keywords from content using simple frequency analysis."""
    words = re.findall(r'\b[a-z]{4,}\b', content.lower())
    
    # Remove stop words
    words = [w for w in words if w not in STOP_WORDS]
    
    # Count frequency
    freq = Counter(words)
    
    # Return top keywords
    return [w for w, _ in freq.most_common(max_keywords)]
```
---
## 6. Concurrency & Safety Model
### 6.1 File Locking Strategy
v1.0 had a race condition: two concurrent Claude Code sessions on the same project would both read the memories file, append their entry, and the last write would silently overwrite the first. v2.0 eliminates this with POSIX file locking.
```python
import fcntl
import os
class FileLock:
    def __init__(self, lock_path, timeout=5.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.fd = None
    
    def __enter__(self):
        os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
        self.fd = open(self.lock_path, "w")
        start_time = time.time()
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.time() - start_time >= self.timeout:
                    raise LockTimeoutError(f"Lock timeout after {self.timeout}s")
                time.sleep(0.1)
    
    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()
class FileLockWindows:
    """Fallback for Windows environments (no fcntl)."""
    def __init__(self, lock_path, timeout=5.0):
        self.lock_path = lock_path + ".lock"
        self.timeout = timeout
    
    def __enter__(self):
        start_time = time.time()
        while os.path.exists(self.lock_path):
            if time.time() - start_time >= self.timeout:
                raise LockTimeoutError(f"Lock timeout after {self.timeout}s")
            time.sleep(0.05)
        open(self.lock_path, "w").close()
        return self
    
    def __exit__(self, *args):
        os.remove(self.lock_path)
def get_file_lock(lock_path):
    """Factory to select correct locking implementation."""
    if os.name == 'nt':
        return FileLockWindows(lock_path)
    return FileLock(lock_path)
```
**Windows Compatibility Note:**
fcntl is POSIX-only. On Windows, LockedInClaude falls back to a lock-file spin-wait approach. The spin-wait has a 5-second timeout before raising a LockTimeoutError.
---
## 7. Machine-Readable Output Contract
Every CLI command in v2.0 emits a structured STATUS line as its first or only line of output.
| **Status Code** | **Meaning** | **Example** |
|-----------------|-------------|-------------|
| STATUS:OK | Operation succeeded | `STATUS:OK id=a1b2c3d4 longterm=3 transient=1` |
| STATUS:SKIP | Operation skipped (non-error) | `STATUS:SKIP duplicate content hash` |
| STATUS:WARN | Succeeded with warning | `STATUS:WARN keywords truncated to 20` |
| STATUS:ERROR | Operation failed | `STATUS:ERROR code=E003 msg=invalid JSON` |
| STATUS:DRY | Dry-run preview only | `STATUS:DRY would store 1 entry to project=zap` |
Claude should always check the STATUS token before parsing further output.
---
## 8. Session Archival (v2.0 Fix)
### 8.1 The Problem with v1.0
In v1.0, session archival was triggered only when writing a new task — not at session start or query time. This meant stale sessions could persist indefinitely.
### 8.2 v2.0 Solution
**Trigger at multiple points:**
1. **Session init** (in store_transient): Check if session is stale on first write
2. **Query time** (in query.py): Validate active session freshness
3. **Time-based** (in maintain.py): Vacuum sessions older than N days
```python
def ensure_fresh_session(project):
    """Ensure active session is current."""
    session_file = os.path.join(base_dir, "transient/projects", project, "session.json")
    
    if not os.path.exists(session_file):
        return create_new_session(project)
    
    session = read_json(session_file)
    
    if not session.get("is_active", False):
        archive_session(project, session["session_id"])
        return create_new_session(project)
    
    # Check if session is stale (> 24 hours)
    session_age = datetime.now() - parse_iso(session["session_start"])
    if session_age > timedelta(hours=24):
        archive_session(project, session["session_id"])
        return create_new_session(project)
    
    return session
```
---
## 9. Self-Healing Index (v2.0 Fix)
### 9.1 The Problem with v1.0
If a memories.json file was manually edited or deleted, the index went stale with no self-healing.
### 9.2 v2.0 Solution
```python
def validate_index(base_dir):
    """Validate and heal index on startup."""
    index = read_json(os.path.join(base_dir, "longterm/index.json"))
    healed = []
    
    for entry in list(index["entries"]):
        file_path = os.path.join(base_dir, "longterm", entry["file"])
        
        # Check if file exists
        if not os.path.exists(file_path):
            index["entries"].remove(entry)
            remove_from_keyword_index(index, entry["project"])
            healed.append(f"removed stale: {entry['project']}")
            continue
        
        # Check if checksum matches
        actual_checksum = sha256_file(file_path)
        if actual_checksum != entry.get("checksum"):
            # File changed — reindex
            reindex_entry = {
                "project": entry["project"],
                "file": entry["file"],
            }
            reindex_project_entries(index, reindex_entry)
            healed.append(f"reindexed: {entry['project']}")
    
    write_json(os.path.join(base_dir, "longterm/index.json"), index)
    return healed
```
---
## 10. Query Output Formats
### 10.1 JSON Format (Default)
```json
{
  "query": {
    "project": "zap",
    "keywords": ["journaler"],
    "type": "longterm"
  },
  "results": {
    "longterm": [
      {
        "source": "longterm",
        "project": "zap",
        "file": "~/.locked-in-claude/longterm/projects/zap/memories.json",
        "entries": [
          {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "title": "Journaler Pattern Implementation",
            "type": "context",
            "category": "architecture",
            "preview": "The journaler is the base class that provides logging...",
            "keywords": ["journaler", "base-class", "logging", "pattern"],
            "tags": ["#architecture"],
            "created_at": "2024-01-15T10:30:00Z"
          }
        ]
      }
    ],
    "transient": []
  },
  "status": "OK",
  "total_matches": 1,
  "query_time_ms": 12
}
```
### 10.2 Preview Truncation Strategy
The preview is the first 200 characters of content, truncated at word boundary:
```python
def get_preview(content, max_chars=200):
    if len(content) <= max_chars:
        return content
    
    preview = content[:max_chars]
    last_space = preview.rfind(' ')
    if last_space > max_chars * 0.7:  # Don't cut if >70% is one word
        preview = preview[:last_space]
    
    return preview + "..."
```
---
## 11. Performance Characteristics
| **Operation** | **Complexity** | **Expected Latency (10k entries)** |
|---------------|----------------|-----------------------------------|
| Query by project | O(1) | < 5ms |
| Query by keyword (exact) | O(k) | < 20ms |
| Query by keyword (fuzzy) | O(k) stem lookup + O(m) Jaccard | < 50ms |
| Store new entry | O(e) Jaccard over existing entries | < 30ms |
| Full index rebuild | O(n) + checksum | < 6s |
| Startup validate | O(p) where p = project count | < 100ms |
| Session archive | O(1) | < 10ms |
**Scaling Guidance:**
The Jaccard dedup pass in store.py is O(e) over existing entries per project. At 500+ entries this becomes noticeable (~200ms). For high-write projects, use `--no-fuzzy-dedup` to disable.
### 11.1 Size Limits
| **Resource** | **Limit** | **Behavior on Exceed** |
|--------------|-----------|------------------------|
| Single entry content | 1 MB | Truncated with STATUS:WARN |
| Keywords per entry | 20 | Top 20 by frequency kept; STATUS:WARN |
| Title length | 200 chars | Hard error — rejected |
| Tags per entry | 10 | Extras silently dropped |
| Sessions per project | 100 archived | Oldest auto-vacuumed |
| Projects per instance | Unbounded | Index grows linearly |
---
## 12. Error Handling
| **Code** | **Meaning** | **Recovery Action** |
|----------|-------------|---------------------|
| E001 | Project not found | Create on first write; return empty on read |
| E002 | Duplicate content (exact) | Return existing entry ID in STATUS:SKIP |
| E003 | Corrupted JSON | Run maintain.py --rebuild; log to stderr |
| E004 | File not found (index ref) | Auto-removed by validate(); reindex project |
| E005 | Permission denied | Report file path; suggest chmod 600 |
| E006 | Lock timeout (> 5s) | Retry once; then raise LockTimeoutError |
| E007 | Schema version mismatch | Run migrate.py automatically on next init |
| E008 | Content too large (> 1MB) | Truncate to 1MB; STATUS:WARN |
| E009 | Invalid tag format | Tags must start with #; reject with STATUS:WARN |
---
## 13. Claude Integration
### 13.1 System Prompt Addition
Add to Claude's CLAUDE.md or system prompt at session start:
```
## Context Memory System (LockedInClaude v2.0)
You have access to a local memory system at ~/.locked-in-claude/
ALWAYS check the STATUS: prefix before using any output.
### Retrieve context
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --keywords "term1,term2" --format json
### Retrieve by tag
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --tag "#decision" --full
### Retrieve recent (last 2 hours)
python3 ~/.locked-in-claude/bin/query.py \
  --project <name> --since 2h --recent 10
### Store context
python3 ~/.locked-in-claude/bin/store.py \
  --project <name> --type longterm \
  --title "Description" --content "Full context..." \
  --keywords "term1,term2" --tags "#architecture,#decision"
### Check active session
python3 ~/.locked-in-claude/bin/query.py --project <name> --session
### Discover projects
python3 ~/.locked-in-claude/bin/list.py
ALWAYS query memory when:
- Starting work on a file you have not seen this session
- The user asks about architecture, patterns, or component relationships
- You are about to make a design decision that might contradict prior decisions
```
### 13.2 Recommended Query Workflow
| **Trigger** | **Recommended Query** | **Why** |
|-------------|----------------------|---------|
| Opening a file | `--project X --keywords "filename,component" --recent 5` | Surfaces relevant prior context |
| Architecture question | `--project X --tag "#architecture" --full` | Returns full architectural decisions |
| Bug investigation | `--project X --keywords "bugarea" --tag "#bug"` | Combines content + intent filtering |
| Starting a session | `--project X --session` | Gets current task list and recent file edits |
| Before a major decision | `--project X --tag "#decision" --recent 20` | Avoids contradicting prior decisions |
---
## 14. Security Considerations
- All data stored locally — zero network exposure by design
- File permissions: 600 on all JSON files (set by init.py on creation)
- Lock files: 600 permissions; located in locks/ to prevent /tmp races
- No secrets policy: memory system stores architecture and patterns only — credentials, API keys, and tokens must never be stored
- Content hash prevents accidental re-ingestion of sensitive content under different titles
- Audit trail: every entry has created_at and updated_at; longterm entries are never modified
**Security Reminder:**
LockedInClaude does not enforce the no-secrets policy programmatically. It is the responsibility of the Claude agent and human operator to ensure no credentials are passed as --content or --title arguments.
---
## 15. Implementation Checklist
### Phase 1 — Foundation
- [ ] Create directory structure including locks/ and migrations/
- [ ] Implement init.py with validate_and_heal() and schema version check
- [ ] Implement FileLock with POSIX + Windows fallback
### Phase 2 — Storage
- [ ] Implement normalize_keywords() with stop-word filter and STEM_MAP
- [ ] Implement store.py: SHA-256 exact dedup + Jaccard fuzzy dedup
- [ ] Implement auto-populate of related_entries post-write
- [ ] Implement incremental index update (not full rebuild on every write)
### Phase 3 — Retrieval
- [ ] Implement query.py with exact + stem-match fuzzy keyword lookup
- [ ] Implement --since, --tag, --full, --dry-run flags
- [ ] Remove transient global index; replace with direct file reads
### Phase 4 — Tooling
- [ ] Implement archive.py with init-triggered + time-triggered archival
- [ ] Implement list.py for project discovery
- [ ] Implement migrate.py with v1.0 -> v2.0 migration function
### Phase 5 — Maintenance & Hardening
- [ ] Implement maintain.py --rebuild, --validate, --vacuum with STATUS: output
- [ ] Add file-level checksums to index; test self-healing on manual file edits
- [ ] Verify all commands emit STATUS: line as first output token
### Phase 6 — Integration & Testing
- [ ] Integration test: two concurrent store.py calls on same project — verify no data loss
- [ ] Integration test: corrupt memories.json — verify self-heal on next init
- [ ] Integration test: v1.0 memories file — verify migration runs automatically
- [ ] Integration test: 1000-entry project — verify query latency < 50ms
---
## Appendix A: Entry Types
| **Type** | **Use For** |
|----------|-------------|
| context | General project context, background information |
| architecture | System design, component relationships, data flows |
| pattern | Code patterns, conventions, idioms used in the project |
| relationship | How components, files, or systems relate to each other |
| note | Free-form notes, observations, reminders |
| decision | Architectural or design decisions with rationale |
---
## Appendix B: Quick Reference Commands
```bash
# Initialize system
python3 bin/init.py
# Store a memory
python3 bin/store.py --project zap --type longterm \
  --title "Journaler Pattern" --content "The journaler is..." \
  --keywords "journaler,pattern,architecture" --tags "#decision"
# Query memories
python3 bin/query.py --project zap --keywords "journaler"
# Query by tag
python3 bin/query.py --project zap --tag "#bug"
# Query recent (last 2 hours)
python3 bin/query.py --project zap --since 2h --recent 5
# Get session context
python3 bin/query.py --project zap --session
# List all projects
python3 bin/list.py
# Validate and heal index
python3 bin/maintain.py --validate
# Rebuild index
python3 bin/maintain.py --rebuild
# Vacuum old sessions
python3 bin/maintain.py --vacuum --older-than 30
# Migrate from v1.0 to v2.0
python3 bin/migrate.py --from-version 1.0 --to-version 2.0
```
---
*Document Version: 2.0*
*LockedInClaude Enterprise Edition*
*Zero Dependencies · Fully Offline · Production-Grade*