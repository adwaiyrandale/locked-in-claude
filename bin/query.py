#!/usr/bin/env python3
"""Query memories from LockedInClaude."""

import os
import sys
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import (
    BASE_DIR, now, read_json, parse_iso, normalize_keywords, get_preview
)


def get_project_files(index, project):
    """Get files for a project."""
    for entry in index.get("entries", []):
        if entry["project"] == project:
            return [os.path.join(BASE_DIR, "longterm", entry["file"])]
    return []


def fuzzy_keyword_search(index, project, keywords):
    """Search by keywords with stemming."""
    if not keywords:
        return get_project_files(index, project)
    
    candidates = {}
    normalized = [normalize_keywords([kw])[0] if normalize_keywords([kw]) else kw.lower() for kw in keywords]
    
    for kw in normalized:
        kw = kw.lower()
        
        # Exact match
        for match in index.get("keyword_index", {}).get(kw, []):
            file_path = os.path.join(BASE_DIR, "longterm", match["file"])
            candidates[file_path] = candidates.get(file_path, 0) + 2
        
        # Stem match
        for indexed_kw, matches in index.get("keyword_index", {}).items():
            if indexed_kw.startswith(kw) or kw.startswith(indexed_kw):
                for match in matches:
                    file_path = os.path.join(BASE_DIR, "longterm", match["file"])
                    candidates[file_path] = candidates.get(file_path, 0) + 1
    
    return sorted(candidates.keys(), key=lambda f: candidates[f], reverse=True)


def load_and_filter(matched_files, keywords=None, since=None, tag=None, full=False, summary=False):
    """Load and filter entries from matched files."""
    entries = []
    for file_path in matched_files:
        if not os.path.exists(file_path):
            continue
        data = read_json(file_path)
        if not data:
            continue
        
        for entry in data.get("entries", []):
            # Filter by tag
            if tag and tag not in entry.get("tags", []):
                continue
            
            # Filter by since
            if since:
                entry_time = parse_iso(entry.get("created_at"))
                if entry_time < since:
                    continue
            
            if summary:
                entries.append({
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "tags": entry.get("tags", []),
                    "created_at": entry.get("created_at")
                })
            elif full:
                entries.append(entry)
            else:
                entries.append({
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "type": entry.get("type"),
                    "preview": get_preview(entry.get("content", "")),
                    "tags": entry.get("tags", []),
                    "keywords": entry.get("keywords", []),
                    "created_at": entry.get("created_at")
                })
    
    return entries


def sort_by_time(entries):
    """Sort entries by created_at descending."""
    return sorted(entries, key=lambda e: parse_iso(e.get("created_at", "")), reverse=True)


def get_active_session(project):
    """Get active session for a project."""
    session_file = os.path.join(BASE_DIR, "transient", "projects", project, "session.json")
    return read_json(session_file)


def load_transient_direct(project):
    """Load transient data directly."""
    session = get_active_session(project)
    if session:
        return [session]
    return []


def query(project=None, keywords=None, type="both", recent=0, since=None, tag=None, 
          session=False, full=False, summary=False, limit=0, format="text"):
    """Query memories."""
    results = {"longterm": [], "transient": []}
    
    if type in ["longterm", "both"]:
        index = read_json(os.path.join(BASE_DIR, "longterm", "index.json"))
        if index:
            matched = fuzzy_keyword_search(index, project, keywords or [])
            results["longterm"] = load_and_filter(matched, keywords, since, tag, full, summary)
    
    if type in ["transient", "both"]:
        if session and project:
            results["transient"] = [get_active_session(project)]
        elif project:
            results["transient"] = load_transient_direct(project)
    
    # Apply limit (different from recent - no time sorting)
    if limit > 0:
        for tier in results:
            results[tier] = results[tier][:limit]
    elif recent > 0:
        for tier in results:
            results[tier] = sort_by_time(results[tier])[:recent]
    
    if format == "json":
        print(json.dumps({
            "results": results,
            "status": "OK"
        }, indent=2))
    else:
        total_lt = len(results["longterm"])
        total_tt = len(results["transient"])
        print(f"STATUS:OK longterm={total_lt} transient={total_tt}")
        
        if results["longterm"]:
            print("\n--- LONGTERM ---")
            for i, e in enumerate(results["longterm"], 1):
                print(f"[{i}] {e.get('title', 'Untitled')} ({e.get('type', 'unknown')})")
                if e.get("preview"):
                    print(f"    {e['preview'][:100]}...")
                if e.get("tags"):
                    print(f"    Tags: {', '.join(e['tags'])}")
        
        if results["transient"]:
            print("\n--- TRANSIENT ---")
            for e in results["transient"]:
                print(f"Session: {e.get('session_id', 'unknown')}")
                if e.get("active_tasks"):
                    print(f"  Tasks: {len(e['active_tasks'])}")
                if e.get("session_notes"):
                    print(f"  Notes: {e['session_notes'][:100]}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Query memories")
    parser.add_argument("--project", help="Project name")
    parser.add_argument("--keywords", help="Comma-separated keywords")
    parser.add_argument("--type", choices=["longterm", "transient", "both"], default="both")
    parser.add_argument("--recent", type=int, default=0, help="Get N most recent")
    parser.add_argument("--since", help="Get entries since (e.g., 2h, 7d)")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--session", action="store_true", help="Get current session")
    parser.add_argument("--full", action="store_true", help="Return full content")
    parser.add_argument("--summary", action="store_true", help="Return summary only")
    parser.add_argument("--limit", type=int, default=0, help="Max results")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    # Parse since
    since = None
    if args.since:
        from datetime import timedelta
        value = args.since[:-1]
        unit = args.since[-1]
        try:
            if unit == "h":
                delta = timedelta(hours=int(value))
            elif unit == "d":
                delta = timedelta(days=int(value))
            elif unit == "m":
                delta = timedelta(minutes=int(value))
            else:
                delta = timedelta(hours=int(value))
            since = parse_iso(now()) - delta
        except (ValueError, IndexError):
            print("STATUS:ERROR code=E001 msg=invalid --since format (use like 2h, 7d)")
            sys.exit(1)
    
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    
    query(
        project=args.project,
        keywords=keywords,
        type=args.type,
        recent=args.recent,
        since=since,
        tag=args.tag,
        session=args.session,
        full=args.full,
        summary=args.summary,
        limit=args.limit,
        format=args.format
    )


if __name__ == "__main__":
    main()
