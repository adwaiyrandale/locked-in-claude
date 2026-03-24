#!/usr/bin/env python3
"""Dump memories to shareable file - Blue Lock: "The Dump"."""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, now, read_json, write_json


def read_all_memories(project):
    """Read all memories for a project."""
    mem_file = os.path.join(BASE_DIR, "longterm", "projects", project, "memories.json")
    data = read_json(mem_file)
    return data.get("entries", []) if data else []


def dump_memory(project, output_path=None, format="txt"):
    """Export project memories to a shareable file."""
    memories = read_all_memories(project)
    
    if not output_path:
        output_path = os.path.join(os.getcwd(), f"{project}_memoryDump.txt")
    
    if format == "txt":
        with open(output_path, "w") as f:
            f.write(f"# LockedInClaude Memory Dump\n")
            f.write(f"# Project: {project}\n")
            f.write(f"# Exported: {now()}\n")
            f.write(f"# ============================================\n\n")
            
            for entry in memories:
                f.write(f"## {entry.get('title', 'Untitled')}\n")
                f.write(f"**Type:** {entry.get('type', 'unknown')} | **ID:** {entry.get('id', 'unknown')}\n")
                f.write(f"**Hash:** {entry.get('content_hash', '')}\n")
                f.write(f"**Keywords:** {', '.join(entry.get('keywords', []))}\n")
                f.write(f"**Tags:** {', '.join(entry.get('tags', []))}\n")
                f.write(f"**Created:** {entry.get('created_at')}\n")
                f.write(f"**Updated:** {entry.get('updated_at')}\n\n")
                f.write(f"{entry.get('content', '')}\n\n")
                f.write(f"---\n\n")
        
        print(f"STATUS:OK dumped={len(memories)} file={output_path}")
    else:
        # JSON format
        dump_data = {
            "project": project,
            "exported_at": now(),
            "schema_version": "2.0",
            "entries": memories
        }
        write_json(output_path, dump_data)
        print(f"STATUS:OK dumped={len(memories)} file={output_path}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Dump memories to shareable file")
    parser.add_argument("--project", required=True, help="Project name")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--format", choices=["txt", "json"], default="txt", help="Output format")
    args = parser.parse_args()
    
    dump_memory(args.project, args.output, args.format)


if __name__ == "__main__":
    main()
