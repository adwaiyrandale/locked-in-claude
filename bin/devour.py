#!/usr/bin/env python3
"""Devour/import memories from dump file - Blue Lock: "The Devour"."""

import os
import sys
import argparse
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    BASE_DIR, now, read_json, write_json, normalize_keywords, 
    jaccard_similarity, parse_iso, get_lock, release_lock
)


def find_by_hash(project, content_hash):
    """Find entry by content hash."""
    mem_file = os.path.join(BASE_DIR, "longterm", "projects", project, "memories.json")
    data = read_json(mem_file)
    if not data:
        return None
    
    for entry in data.get("entries", []):
        existing_hash = entry.get("content_hash", "").replace("sha256:", "")
        if existing_hash == content_hash:
            return entry
    return None


def find_fuzzy_duplicate(project, keywords):
    """Find fuzzy duplicate by keyword Jaccard similarity."""
    mem_file = os.path.join(BASE_DIR, "longterm", "projects", project, "memories.json")
    data = read_json(mem_file)
    if not data:
        return None
    
    new_kws = set(keywords)
    for entry in data.get("entries", []):
        existing_kws = set(entry.get("keywords", []))
        jaccard = jaccard_similarity(new_kws, existing_kws)
        if jaccard > 0.85:
            return entry
    return None


def update_entry(project, entry_id, new_data):
    """Update existing entry with newer data."""
    lock_file = os.path.join(BASE_DIR, "locks", f"{project}.lock")
    lock_fd = get_lock(lock_file)
    
    try:
        mem_file = os.path.join(BASE_DIR, "longterm", "projects", project, "memories.json")
        data = read_json(mem_file)
        
        for entry in data.get("entries", []):
            if entry["id"] == entry_id:
                # Update fields
                entry["title"] = new_data.get("title", entry.get("title"))
                entry["content"] = new_data.get("content", entry.get("content"))
                entry["keywords"] = new_data.get("keywords", entry.get("keywords"))
                entry["tags"] = new_data.get("tags", entry.get("tags"))
                entry["updated_at"] = now()
                break
        
        data["last_updated"] = now()
        write_json(mem_file, data)
    
    finally:
        release_lock(lock_fd)


def add_entry(project, entry):
    """Add new entry to project."""
    lock_file = os.path.join(BASE_DIR, "locks", f"{project}.lock")
    lock_fd = get_lock(lock_file)
    
    try:
        proj_dir = os.path.join(BASE_DIR, "longterm", "projects", project)
        os.makedirs(proj_dir, exist_ok=True)
        
        mem_file = os.path.join(proj_dir, "memories.json")
        data = read_json(mem_file)
        
        if not data:
            data = {
                "schema_version": "2.0",
                "project": project,
                "created_at": now(),
                "last_updated": now(),
                "entries": []
            }
        
        # Add new ID if not present
        if "id" not in entry:
            import uuid
            entry["id"] = str(uuid.uuid4())
        
        data["entries"].append(entry)
        data["last_updated"] = now()
        
        write_json(mem_file, data)
    
    finally:
        release_lock(lock_fd)


def devour_memory(file_path, project=None, merge=False):
    """Import/ingest memories from a dump file."""
    # Check if file is JSON or TXT
    data = None
    is_json = False
    
    with open(file_path, "r") as f:
        first_char = f.read(1)
    
    if first_char == "{" or first_char == "[":
        # Try JSON
        try:
            data = read_json(file_path)
            is_json = True
        except:
            pass
    
    if not data and not is_json:
        # Parse txt format
        with open(file_path, "r") as f:
            content = f.read()
        
        if content.startswith("# LockedInClaude"):
            # Parse txt format
            entries = []
            current_entry = None
            current_content = []
            in_content = False
            
            for line in content.split("\n"):
                if line.startswith("## "):
                    if current_entry:
                        current_entry["content"] = "\n".join(current_content).strip()
                        entries.append(current_entry)
                    current_entry = {
                        "title": line[3:].strip(),
                        "type": "unknown",
                        "keywords": [],
                        "tags": [],
                        "content": ""
                    }
                    current_content = []
                    in_content = False
                elif current_entry:
                    if line.startswith("**Type:**"):
                        parts = line.replace("**", "").split("|")
                        for p in parts:
                            if "Type:" in p:
                                current_entry["type"] = p.split(":")[1].strip()
                            elif "ID:" in p:
                                current_entry["id"] = p.split(":")[1].strip()
                    elif line.startswith("**Hash:**"):
                        current_entry["content_hash"] = line.replace("**", "").split(":")[1].strip()
                    elif line.startswith("**Keywords:**"):
                        kws = line.replace("**", "").split(":")[1].strip()
                        current_entry["keywords"] = [k.strip() for k in kws.split(",") if k.strip()]
                    elif line.startswith("**Tags:**"):
                        tags = line.replace("**", "").split(":")[1].strip()
                        current_entry["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
                    elif line.startswith("**Created:**"):
                        current_entry["created_at"] = line.replace("**", "").split(":")[1].strip()
                    elif line.startswith("**Updated:**"):
                        current_entry["updated_at"] = line.replace("**", "").split(":")[1].strip()
                    elif line.strip() == "---":
                        in_content = True
                    elif in_content:
                        current_content.append(line)
            
            if current_entry:
                current_entry["content"] = "\n".join(current_content).strip()
                entries.append(current_entry)
            
            data = {
                "project": None,
                "entries": entries
            }
        else:
            print("STATUS:ERROR code=E003 msg=invalid dump file format")
            return None
    
    imported_project = data.get("project")
    entries = data.get("entries", [])
    
    target_project = project or imported_project
    
    if not target_project:
        print("STATUS:ERROR code=E001 msg=no project specified")
        return None
    
    imported_count = 0
    skipped_count = 0
    updated_count = 0
    
    for entry in entries:
        # Check for duplicates by content hash
        content_hash = entry.get("content_hash", "")
        if not content_hash:
            content_hash = "sha256:" + hashlib.sha256(entry.get("content", "").encode()).hexdigest()
        
        existing = find_by_hash(target_project, content_hash.replace("sha256:", ""))
        
        if existing:
            # Check if imported is newer
            imported_updated = parse_iso(entry.get("updated_at") or entry.get("created_at"))
            existing_updated = parse_iso(existing.get("updated_at") or existing.get("created_at"))
            
            if imported_updated > existing_updated:
                update_entry(target_project, existing["id"], entry)
                updated_count += 1
            else:
                skipped_count += 1
            continue
        
        # Check fuzzy duplicate
        keywords = normalize_keywords(entry.get("keywords", []))
        fuzzy_match = find_fuzzy_duplicate(target_project, keywords)
        if fuzzy_match:
            skipped_count += 1
            continue
        
        # Import new entry
        add_entry(target_project, entry)
        imported_count += 1
    
    # Rebuild index
    from maintain import rebuild_index
    rebuild_index()
    
    result = {"imported": imported_count, "updated": updated_count, "skipped": skipped_count}
    print(f"STATUS:OK imported={imported_count} updated={updated_count} skipped={skipped_count}")
    
    return result


def main():
    parser = argparse.ArgumentParser(description="Devour/import memories from dump file")
    parser.add_argument("--file", required=True, help="Dump file to import")
    parser.add_argument("--project", help="Target project name (overrides dump project)")
    parser.add_argument("--merge", action="store_true", help="Merge into existing project")
    args = parser.parse_args()
    
    devour_memory(args.file, args.project, args.merge)


if __name__ == "__main__":
    main()
