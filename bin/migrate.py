#!/usr/bin/env python3
"""Migrate schema in LockedInClaude."""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, CURRENT_VERSION, now, read_json, write_json
import base64


def migrate_v1_to_v2():
    """Migrate from v1.0 to v2.0."""
    migrated = []
    
    # Migrate longterm memories
    projects_dir = os.path.join(BASE_DIR, "longterm", "projects")
    if os.path.exists(projects_dir):
        for proj in os.listdir(projects_dir):
            proj_dir = os.path.join(projects_dir, proj)
            if not os.path.isdir(proj_dir):
                continue
            
            mem_file = os.path.join(proj_dir, "memories.json")
            if not os.path.exists(mem_file):
                continue
            
            data = read_json(mem_file)
            if not data:
                continue
            
            # Add schema_version to file
            data["schema_version"] = "2.0"
            
            # Add tags and keyword_fingerprint to each entry
            for entry in data.get("entries", []):
                if "tags" not in entry:
                    entry["tags"] = []
                if "keyword_fingerprint" not in entry:
                    kws = entry.get("keywords", [])
                    entry["keyword_fingerprint"] = base64.b64encode(",".join(sorted(kws)).encode()).decode()
            
            write_json(mem_file, data)
            migrated.append(f"longterm:{proj}")
    
    # Update index
    index_path = os.path.join(BASE_DIR, "longterm", "index.json")
    index = read_json(index_path)
    if index:
        index["schema_version"] = "2.0"
        write_json(index_path, index)
    
    print(f"STATUS:OK migrated={len(migrated)}")
    return migrated


def main():
    parser = argparse.ArgumentParser(description="Migrate schema")
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    if args.dry_run:
        print(f"STATUS:DRY would migrate {args.from_version} -> {args.to_version}")
        return
    
    if args.from_version == "1.0" and args.to_version == "2.0":
        migrate_v1_to_v2()
    else:
        print(f"STATUS:ERROR code=E007 msg=no migration path {args.from_version} -> {args.to_version}")


if __name__ == "__main__":
    main()
