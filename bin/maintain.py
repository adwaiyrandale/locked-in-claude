#!/usr/bin/env python3
"""Maintain index in LockedInClaude."""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, CURRENT_VERSION, now, read_json, write_json, sha256_file


def rebuild_index():
    """Rebuild entire index from scratch."""
    index = {
        "schema_version": CURRENT_VERSION,
        "type": "longterm",
        "last_full_reindex": now(),
        "entries": [],
        "keyword_index": {}
    }
    
    projects_dir = os.path.join(BASE_DIR, "longterm", "projects")
    if not os.path.exists(projects_dir):
        print("STATUS:OK rebuild complete (no projects)")
        return
    
    for proj in os.listdir(projects_dir):
        proj_dir = os.path.join(projects_dir, proj)
        if not os.path.isdir(proj_dir):
            continue
        
        mem_file = os.path.join(proj_dir, "memories.json")
        if not os.path.exists(mem_file):
            continue
        
        data = read_json(mem_file)
        entries = data.get("entries", []) if data else []
        
        project_keywords = set()
        for entry in entries:
            for kw in entry.get("keywords", []):
                kw_lower = kw.lower()
                project_keywords.add(kw_lower)
                
                if kw_lower not in index["keyword_index"]:
                    index["keyword_index"][kw_lower] = []
                
                refs = index["keyword_index"][kw_lower]
                if not any(r.get("project") == proj for r in refs):
                    refs.append({
                        "project": proj,
                        "file": f"projects/{proj}/memories.json"
                    })
        
        file_size = os.path.getsize(mem_file) if os.path.exists(mem_file) else 0
        
        index["entries"].append({
            "project": proj,
            "file": f"projects/{proj}/memories.json",
            "keywords": list(project_keywords),
            "entry_count": len(entries),
            "checksum": sha256_file(mem_file),
            "total_size_bytes": file_size,
            "last_updated": data.get("last_updated") if data else None
        })
    
    index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    write_json(index_path, index)
    
    print(f"STATUS:OK rebuild complete projects={len(index['entries'])}")


def validate_index():
    """Validate and heal index."""
    index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    index = read_json(index_path)
    
    if not index:
        print("STATUS:ERROR code=E003 msg=no index found")
        return
    
    healed = []
    stale_projects = set()
    
    for entry in list(index.get("entries", [])):
        file_path = os.path.join(BASE_DIR, "longterm", entry["file"])
        
        if not os.path.exists(file_path):
            stale_projects.add(entry["project"])
            healed.append(f"removed: {entry['project']}")
            continue
        
        actual_checksum = sha256_file(file_path)
        if actual_checksum != entry.get("checksum"):
            healed.append(f"changed: {entry['project']}")
    
    # Filter stale entries
    index["entries"] = [e for e in index["entries"] if e["project"] not in stale_projects]
    
    # Clean keyword index
    for proj in stale_projects:
        for kw, refs in list(index.get("keyword_index", {}).items()):
            index["keyword_index"][kw] = [r for r in refs if r.get("project") != proj]
    
    if healed or stale_projects:
        write_json(index_path, index)
    
    print(f"STATUS:OK validate complete healed={len(healed)}")


def vacuum_sessions(older_than_days=30):
    """Vacuum old sessions."""
    from datetime import timedelta
    from utils import parse_iso
    
    cutoff = parse_iso(now()) - timedelta(days=older_than_days)
    cleaned = 0
    
    trans_projects = os.path.join(BASE_DIR, "transient", "projects")
    if not os.path.exists(trans_projects):
        print("STATUS:OK vacuum complete (no projects)")
        return
    
    for proj in os.listdir(trans_projects):
        proj_dir = os.path.join(trans_projects, proj)
        if not os.path.isdir(proj_dir):
            continue
        
        sessions_dir = os.path.join(proj_dir, "sessions")
        if not os.path.exists(sessions_dir):
            continue
        
        for sess_file in os.listdir(sessions_dir):
            if not sess_file.endswith(".json"):
                continue
            
            sess_path = os.path.join(sessions_dir, sess_file)
            session = read_json(sess_path)
            
            if not session:
                continue
            
            end_time = parse_iso(session.get("session_end"))
            if end_time < cutoff:
                os.remove(sess_path)
                cleaned += 1
    
    print(f"STATUS:OK vacuum complete cleaned={cleaned}")


def main():
    parser = argparse.ArgumentParser(description="Maintain index")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index")
    parser.add_argument("--validate", action="store_true", help="Validate index")
    parser.add_argument("--vacuum", action="store_true", help="Vacuum old sessions")
    parser.add_argument("--older-than", type=int, default=30, help="Days for vacuum")
    args = parser.parse_args()
    
    if args.rebuild:
        rebuild_index()
    elif args.validate:
        validate_index()
    elif args.vacuum:
        vacuum_sessions(args.older_than)
    else:
        print("STATUS:ERROR code=E001 msg=no action specified")


if __name__ == "__main__":
    main()
