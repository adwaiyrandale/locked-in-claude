#!/usr/bin/env python3
"""Initialize LockedInClaude system."""

import os
import sys
import argparse

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, CURRENT_VERSION, write_json, read_json, sha256_file


def create_directories():
    """Create all required directories."""
    dirs = [
        os.path.join(BASE_DIR, "longterm", "projects"),
        os.path.join(BASE_DIR, "transient", "projects"),
        os.path.join(BASE_DIR, "locks"),
        os.path.join(BASE_DIR, "migrations"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def create_index(path, index_type):
    """Create an empty index file."""
    write_json(path, {
        "schema_version": CURRENT_VERSION,
        "type": index_type,
        "last_full_reindex": None,
        "entries": [],
        "keyword_index": {}
    })


def validate_and_heal(base_dir):
    """Validate and heal index on startup."""
    index_path = os.path.join(base_dir, "longterm", "index.json")
    index = read_json(index_path)
    
    if not index:
        print("STATUS:WARN no index found, running init")
        return False
    
    if index.get("schema_version") != CURRENT_VERSION:
        print(f"STATUS:WARN schema mismatch: {index.get('schema_version')} != {CURRENT_VERSION}")
    
    healed = []
    stale_projects = set()
    
    for entry in list(index.get("entries", [])):
        file_path = os.path.join(base_dir, "longterm", entry["file"])
        
        if not os.path.exists(file_path):
            stale_projects.add(entry["project"])
            healed.append(f"removed stale: {entry['project']}")
            continue
        
        actual_checksum = sha256_file(file_path)
        if actual_checksum != entry.get("checksum"):
            # File changed - reindex
            reindex_project(index, entry["project"])
            healed.append(f"reindexed: {entry['project']}")
    
    # Filter stale entries
    index["entries"] = [e for e in index["entries"] if e["project"] not in stale_projects]
    
    # Clean keyword index
    for proj in stale_projects:
        if proj in index.get("keyword_index", {}):
            del index["keyword_index"][proj]
    
    if healed:
        write_json(index_path, index)
    
    print(f"STATUS:OK validate complete. healed={len(healed)}")
    return True


def reindex_project(index, project):
    """Rebuild all keyword index entries for a single project."""
    memories_file = os.path.join(BASE_DIR, "longterm", "projects", project, "memories.json")
    if not os.path.exists(memories_file):
        return
    
    data = read_json(memories_file)
    entries = data.get("entries", []) if data else []
    
    project_keywords = set()
    for entry in entries:
        for kw in entry.get("keywords", []):
            kw_lower = kw.lower()
            project_keywords.add(kw_lower)
            
            if "keyword_index" not in index:
                index["keyword_index"] = {}
            
            if kw_lower not in index["keyword_index"]:
                index["keyword_index"][kw_lower] = []
            
            existing_refs = index["keyword_index"][kw_lower]
            if not any(r.get("project") == project for r in existing_refs):
                existing_refs.append({
                    "project": project,
                    "file": f"projects/{project}/memories.json"
                })
    
    # Update project entry in index
    for entry in index["entries"]:
        if entry["project"] == project:
            entry["keywords"] = list(project_keywords)
            entry["entry_count"] = len(entries)
            entry["checksum"] = sha256_file(memories_file)
            entry["last_updated"] = data.get("last_updated") if data else None
            break


def init(force=False, validate_only=False):
    """Initialize the system."""
    if validate_only:
        return validate_and_heal(BASE_DIR)
    
    if os.path.exists(BASE_DIR) and not force:
        return validate_and_heal(BASE_DIR)
    
    create_directories()
    
    # Create longterm index
    lt_index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    if not os.path.exists(lt_index_path):
        create_index(lt_index_path, "longterm")
    
    print("STATUS:OK init complete")
    return validate_and_heal(BASE_DIR)


def main():
    parser = argparse.ArgumentParser(description="Initialize LockedInClaude")
    parser.add_argument("--force", action="store_true", help="Force reinitialize")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing")
    args = parser.parse_args()
    
    init(force=args.force, validate_only=args.validate_only)


if __name__ == "__main__":
    main()
