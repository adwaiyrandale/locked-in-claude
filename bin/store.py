#!/usr/bin/env python3
"""Store memories in LockedInClaude."""

import os
import sys
import argparse
import hashlib
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    BASE_DIR, CURRENT_VERSION, now, write_json, read_json,
    normalize_keywords, extract_keywords, find_related,
    auto_detect_type, truncate, jaccard_similarity
)


def get_lock(lock_path, timeout=5.0):
    """Get file lock."""
    import fcntl
    import time
    
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    fd = open(lock_path, "w")
    start = time.time()
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.time() - start >= timeout:
                fd.close()
                print(f"STATUS:ERROR code=E006 msg=lock timeout")
                sys.exit(1)
            time.sleep(0.1)


def release_lock(fd):
    """Release file lock."""
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()


def load_or_create_memories(project, memory_type="longterm"):
    """Load or create memories file for a project."""
    subdir = memory_type if memory_type == "longterm" else "transient"
    proj_dir = os.path.join(BASE_DIR, subdir, "projects", project)
    os.makedirs(proj_dir, exist_ok=True)
    
    if memory_type == "longterm":
        mem_file = os.path.join(proj_dir, "memories.json")
    else:
        mem_file = os.path.join(proj_dir, "session.json")
    
    if os.path.exists(mem_file):
        return read_json(mem_file), mem_file
    
    if memory_type == "longterm":
        return {
            "schema_version": CURRENT_VERSION,
            "project": project,
            "created_at": now(),
            "last_updated": now(),
            "entries": []
        }, mem_file
    else:
        return {
            "schema_version": CURRENT_VERSION,
            "project": project,
            "session_id": str(uuid.uuid4()),
            "session_start": now(),
            "session_end": None,
            "is_active": True,
            "active_tasks": [],
            "recent_context": [],
            "session_notes": "",
            "referenced_memories": []
        }, mem_file


def update_index(project, entry, keywords):
    """Update global index with new entry."""
    index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    index = read_json(index_path)
    
    if not index:
        index = {
            "schema_version": CURRENT_VERSION,
            "type": "longterm",
            "last_full_reindex": now(),
            "entries": [],
            "keyword_index": {}
        }
    
    # Update project entry
    proj_entry = None
    for e in index.get("entries", []):
        if e["project"] == project:
            proj_entry = e
            break
    
    if not proj_entry:
        proj_entry = {
            "project": project,
            "file": f"projects/{project}/memories.json",
            "keywords": [],
            "entry_count": 0,
            "checksum": "",
            "total_size_bytes": 0,
            "last_updated": now()
        }
        index["entries"].append(proj_entry)
    
    proj_entry["entry_count"] = proj_entry.get("entry_count", 0) + 1
    proj_entry["last_updated"] = now()
    
    # Update keyword index
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in index.get("keyword_index", {}):
            index["keyword_index"][kw_lower] = []
        
        refs = index["keyword_index"][kw_lower]
        if not any(r.get("project") == project for r in refs):
            refs.append({
                "project": project,
                "file": f"projects/{project}/memories.json",
                "entry_ids": []
            })
    
    index["last_full_reindex"] = now()
    write_json(index_path, index)


def store_longterm(project, title, content, keywords, category="context", tags=None, no_fuzzy_dedup=False):
    """Store a longterm memory."""
    if tags is None:
        tags = []
    
    lock_file = os.path.join(BASE_DIR, "locks", f"{project}.lock")
    lock_fd = get_lock(lock_file)
    
    try:
        data, mem_file = load_or_create_memories(project, "longterm")
        
        # Step 1: Exact dedup via SHA-256
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        existing_hashes = {e["content_hash"].replace("sha256:", "") for e in data.get("entries", [])}
        if content_hash in existing_hashes:
            print("STATUS:SKIP duplicate content hash")
            return None
        
        # Step 2: Fuzzy dedup via Jaccard
        if not no_fuzzy_dedup:
            new_kws = set(normalize_keywords(keywords))
            for existing in data.get("entries", []):
                existing_kws = set(existing.get("keywords", []))
                jaccard = jaccard_similarity(new_kws, existing_kws)
                if jaccard > 0.85:
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
            "created_at": now(),
            "updated_at": now()
        }
        
        # Step 4: Auto-populate related_entries
        entry["related_entries"] = find_related(data.get("entries", []), cleaned_kws)
        
        if "entries" not in data:
            data["entries"] = []
        data["entries"].append(entry)
        data["last_updated"] = now()
        
        write_json(mem_file, data)
        update_index(project, entry, cleaned_kws)
        
        print(f"STATUS:OK id={entry['id']}")
        return entry["id"]
    
    finally:
        release_lock(lock_fd)


def store_transient(project, task, status="pending", priority="medium", tags=None):
    """Store a transient task."""
    if tags is None:
        tags = []
    
    lock_file = os.path.join(BASE_DIR, "locks", f"{project}.session.lock")
    lock_fd = get_lock(lock_file)
    
    try:
        data, session_file = load_or_create_memories(project, "transient")
        
        # Check if session is stale (24 hours)
        from utils import parse_iso
        session_start = parse_iso(data.get("session_start"))
        if (parse_iso(now()) - session_start) > timedelta(hours=24):
            # Archive old session
            archive_session(project, data["session_id"])
            data, session_file = load_or_create_memories(project, "transient")
        
        task_entry = {
            "id": f"task-{str(uuid.uuid4())[:8]}",
            "description": task,
            "status": status,
            "priority": priority,
            "tags": [t.lower() for t in tags if t.startswith("#")],
            "created_at": now()
        }
        
        if "active_tasks" not in data:
            data["active_tasks"] = []
        data["active_tasks"].append(task_entry)
        
        write_json(session_file, data)
        
        print(f"STATUS:OK id={task_entry['id']}")
        return task_entry["id"]
    
    finally:
        release_lock(lock_fd)


def archive_session(project, session_id):
    """Archive a session."""
    session_file = os.path.join(BASE_DIR, "transient", "projects", project, "session.json")
    sessions_dir = os.path.join(BASE_DIR, "transient", "projects", project, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    
    session = read_json(session_file)
    if not session:
        return
    
    session["session_end"] = now()
    session["is_active"] = False
    
    archive_file = os.path.join(sessions_dir, f"{session_id}.json")
    write_json(archive_file, session)


def main():
    parser = argparse.ArgumentParser(description="Store a memory")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--type", choices=["longterm", "transient"], default="longterm", help="Memory type")
    parser.add_argument("--auto", action="store_true", help="Auto-detect memory type")
    parser.add_argument("--title", help="Memory title (for longterm)")
    parser.add_argument("--content", help="Memory content")
    parser.add_argument("--keywords", help="Comma-separated keywords")
    parser.add_argument("--tags", help="Comma-separated tags")
    parser.add_argument("--category", default="context", help="Memory category")
    parser.add_argument("--no-fuzzy-dedup", action="store_true", help="Disable fuzzy dedup")
    parser.add_argument("--stdin", action="store_true", help="Read content from stdin")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()
    
    # Get content from stdin if requested
    content = args.content
    if args.stdin:
        content = sys.stdin.read()
    
    if not content:
        print("STATUS:ERROR code=E001 msg=no content provided")
        sys.exit(1)
    
    keywords = []
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]
    
    # Determine memory type
    if args.auto:
        memory_type = auto_detect_type(content, args.title or "", keywords)
    else:
        memory_type = args.type
    
    if args.dry_run:
        print(f"STATUS:DRY would store to project={args.project} type={memory_type}")
        return
    
    if memory_type == "longterm":
        if not args.title:
            print("STATUS:ERROR code=E001 msg=title required for longterm")
            sys.exit(1)
        store_longterm(
            args.project, args.title, content, keywords,
            args.category, tags, args.no_fuzzy_dedup
        )
    else:
        store_transient(
            args.project, content, tags=tags
        )


if __name__ == "__main__":
    from datetime import timedelta
    main()
