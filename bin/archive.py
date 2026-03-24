#!/usr/bin/env python3
"""Archive sessions in LockedInClaude."""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import BASE_DIR, now, read_json, write_json


def archive_session(project):
    """Archive current session for a project."""
    session_file = os.path.join(BASE_DIR, "transient", "projects", project, "session.json")
    session = read_json(session_file)
    
    if not session:
        print(f"STATUS:ERROR code=E001 msg=no session found for project {project}")
        return False
    
    if not session.get("is_active"):
        print(f"STATUS:WARN session already archived")
        return False
    
    # Archive
    sessions_dir = os.path.join(BASE_DIR, "transient", "projects", project, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)
    
    session_id = session.get("session_id")
    session["session_end"] = now()
    session["is_active"] = False
    
    archive_file = os.path.join(sessions_dir, f"{session_id}.json")
    write_json(archive_file, session)
    
    # Create new session
    import uuid
    new_session = {
        "schema_version": session.get("schema_version", "2.0"),
        "project": project,
        "session_id": str(uuid.uuid4()),
        "session_start": now(),
        "session_end": None,
        "is_active": True,
        "active_tasks": [],
        "recent_context": [],
        "session_notes": "",
        "referenced_memories": []
    }
    write_json(session_file, new_session)
    
    print(f"STATUS:OK archived={session_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Archive session")
    parser.add_argument("--project", required=True, help="Project name")
    args = parser.parse_args()
    
    archive_session(args.project)


if __name__ == "__main__":
    main()
