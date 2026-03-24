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
        
        if "id" not in entry:
            import uuid
            entry["id"] = str(uuid.uuid4())
        
        data["entries"].append(entry)
        data["last_updated"] = now()
        
        write_json(mem_file, data)
        return entry["id"]
    
    finally:
        release_lock(lock_fd)


def update_index_incremental(project, keywords):
    """Update index for a single project (incremental)."""
    index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    index = read_json(index_path)
    
    if not index:
        return
    
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
                "file": f"projects/{project}/memories.json"
            })
    
    index["last_full_reindex"] = now()
    write_json(index_path, index)


def validate_dump_file(data):
    """Validate dump file has required structure."""
    if not isinstance(data, dict):
        return False, "not a dictionary"
    
    if "entries" not in data:
        return False, "missing 'entries' key"
    
    if not isinstance(data.get("entries"), list):
        return False, "'entries' is not a list"
    
    return True, None


def devour_memory(file_path, project=None, merge=False, merge_strategy="newest", dry_run=False):
    """Import/ingest memories from a dump file."""
    # Read and detect format
    with open(file_path, "r") as f:
        first_char = f.read(1)
    
    data = None
    is_json = False
    
    if first_char == "{" or first_char == "[":
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
            entries = []
            current_entry = None
            current_content = []
            in_content = False
            
            for line in content.split("\n"):
                if line.startswith("## "):
                    if current_entry:
                        current_entry["content"] = "\n".join(current_content).strip()
                        entries.append(current_entry)
                    
                    # Extract title and optional [project] bracket from --all dumps
                    title_part = line[3:].strip()
                    source_project = None
                    if title_part.endswith("]"):
                        bracket_start = title_part.rfind("[")
                        if bracket_start > 0:
                            source_project = title_part[bracket_start+1:-1]
                            title_part = title_part[:bracket_start].strip()
                    
                    current_entry = {
                        "title": title_part,
                        "type": "unknown",
                        "keywords": [],
                        "tags": [],
                        "content": ""
                    }
                    if source_project:
                        current_entry["_source_project"] = source_project
                    
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
    
    if not data:
        print("STATUS:ERROR code=E003 msg=invalid dump file format")
        return None
    
    # Validate structure
    valid, error = validate_dump_file(data)
    if not valid:
        print(f"STATUS:ERROR code=E003 msg=invalid dump: {error}")
        return None
    
    entries = data.get("entries", [])
    is_all_dump = "_source_project" in entries[0] if entries else False
    
    imported_project = data.get("project")
    target_project = project or imported_project
    
    if not target_project and not is_all_dump:
        print("STATUS:ERROR code=E001 msg=no project specified")
        return None
    
    imported_count = 0
    skipped_count = 0
    updated_count = 0
    
    # Process entries
    for entry in entries:
        # Determine target project for this entry
        if is_all_dump:
            entry_project = entry.get("_source_project")
            if not entry_project:
                continue
        else:
            entry_project = target_project
        
        if not entry_project:
            continue
        
        # Check for duplicates by content hash
        content_hash = entry.get("content_hash", "")
        if not content_hash:
            content_hash = "sha256:" + hashlib.sha256(entry.get("content", "").encode()).hexdigest()
        
        existing = find_by_hash(entry_project, content_hash.replace("sha256:", ""))
        
        if existing:
            if merge_strategy == "skip":
                skipped_count += 1
                continue
            
            if merge_strategy == "overwrite":
                update_entry(entry_project, existing["id"], entry)
                updated_count += 1
                continue
            
            # newest (default)
            imported_updated = parse_iso(entry.get("updated_at") or entry.get("created_at"))
            existing_updated = parse_iso(existing.get("updated_at") or existing.get("created_at"))
            
            if imported_updated > existing_updated:
                update_entry(entry_project, existing["id"], entry)
                updated_count += 1
            else:
                skipped_count += 1
            continue
        
        # Check fuzzy duplicate
        keywords = normalize_keywords(entry.get("keywords", []))
        fuzzy_match = find_fuzzy_duplicate(entry_project, keywords)
        if fuzzy_match:
            if merge_strategy != "overwrite":
                skipped_count += 1
                continue
        
        # Import new entry
        if dry_run:
            imported_count += 1
        else:
            new_id = add_entry(entry_project, entry)
            if new_id:
                imported_count += 1
                # Incremental index update
                update_index_incremental(entry_project, keywords)
    
    if not dry_run:
        print(f"STATUS:OK imported={imported_count} updated={updated_count} skipped={skipped_count}")
    else:
        print(f"STATUS:DRY imported={imported_count} updated={updated_count} skipped={skipped_count}")
    
    return {"imported": imported_count, "updated": updated_count, "skipped": skipped_count}


def main():
    parser = argparse.ArgumentParser(description="Devour/import memories from dump file")
    parser.add_argument("--file", required=True, help="Dump file to import")
    parser.add_argument("--project", help="Target project name (overrides dump project)")
    parser.add_argument("--merge", action="store_true", help="Merge into existing project")
    parser.add_argument("--merge-strategy", choices=["skip", "overwrite", "newest"], default="newest",
                        help="How to handle conflicts: skip (keep existing), overwrite (replace), newest (update if imported is newer)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't actually import")
    args = parser.parse_args()
    
    devour_memory(args.file, args.project, args.merge, args.merge_strategy, args.dry_run)


if __name__ == "__main__":
    main()
