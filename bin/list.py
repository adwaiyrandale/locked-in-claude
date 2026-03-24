#!/usr/bin/env python3
"""List projects in LockedInClaude."""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, read_json


def list_projects(type="longterm", format="text"):
    """List all projects."""
    projects = []
    
    if type in ["longterm", "both"]:
        index_path = os.path.join(BASE_DIR, "longterm", "index.json")
        index = read_json(index_path)
        if index:
            for entry in index.get("entries", []):
                projects.append({
                    "name": entry.get("project"),
                    "type": "longterm",
                    "entries": entry.get("entry_count", 0),
                    "last_updated": entry.get("last_updated")
                })
    
    if type in ["transient", "both"]:
        trans_dir = os.path.join(BASE_DIR, "transient", "projects")
        if os.path.exists(trans_dir):
            for proj in os.listdir(trans_dir):
                proj_dir = os.path.join(trans_dir, proj)
                if os.path.isdir(proj_dir):
                    session_file = os.path.join(proj_dir, "session.json")
                    session = read_json(session_file)
                    if session:
                        projects.append({
                            "name": proj,
                            "type": "transient",
                            "session_id": session.get("session_id"),
                            "is_active": session.get("is_active"),
                            "tasks": len(session.get("active_tasks", []))
                        })
    
    if format == "json":
        import json
        print(json.dumps(projects, indent=2))
    else:
        count = len(projects)
        print(f"STATUS:OK count={count}")
        for p in projects:
            if p["type"] == "longterm":
                print(f"  {p['name']}: {p['entries']} entries, last_updated={p.get('last_updated', 'unknown')}")
            else:
                active = "active" if p.get("is_active") else "inactive"
                print(f"  {p['name']}: {p['tasks']} tasks ({active})")
    
    return projects


def main():
    parser = argparse.ArgumentParser(description="List projects")
    parser.add_argument("--type", choices=["longterm", "transient", "both"], default="both")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    list_projects(args.type, args.format)


if __name__ == "__main__":
    main()
