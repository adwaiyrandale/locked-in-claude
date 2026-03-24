import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from collections import Counter

BASE_DIR = os.path.expanduser("~/.locked-in-claude")
CURRENT_VERSION = "2.0"

STEM_MAP = {
    "authentication": "auth",
    "authorization": "authz",
    "authenticated": "auth",
    "authorized": "authz",
    "journaling": "journal",
    "journaler": "journal",
    "logging": "log",
    "logger": "log",
    "implementation": "impl",
    "implementing": "impl",
    "configuration": "config",
    "configuring": "config",
    "initialization": "init",
    "initializing": "init",
    "handlers": "handler",
    "services": "service",
    "clients": "client",
    "servers": "server",
}

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at",
    "to", "for", "of", "with", "by", "from", "is", "are",
    "was", "were", "be", "been", "have", "has", "do", "does"
}


def now():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(ts):
    if not ts:
        return datetime.min
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return datetime.min


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


def sha256_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def truncate(content, max_len):
    if len(content) > max_len:
        return content[:max_len] + "... [truncated]"
    return content


def normalize_keywords(keywords):
    """Multi-stage keyword normalization."""
    result = []
    for kw in keywords:
        kw = kw.lower().strip()
        
        if not kw or kw in STOP_WORDS:
            continue
        
        # Check STEM_MAP first before generic suffix strip
        if kw in STEM_MAP:
            kw = STEM_MAP[kw]
        else:
            # Apply stemming only if not in STEM_MAP
            for suffix in ["ing", "ed", "er", "s", "tion", "ly"]:
                if kw.endswith(suffix) and len(kw) > 4:
                    stemmed = kw[:-len(suffix)]
                    kw = STEM_MAP.get(stemmed, stemmed)
                    break
        
        kw = STEM_MAP.get(kw, kw)
        if kw and kw not in result:
            result.append(kw)
    
    return result[:20]


def extract_keywords(content, max_keywords=10, min_freq=2):
    """Extract keywords from content using simple frequency analysis."""
    words = []
    for word in content.lower().split():
        cleaned = ''.join(c for c in word if c.isalnum())
        if len(cleaned) >= 4:
            words.append(cleaned)
    
    words = [w for w in words if w not in STOP_WORDS]
    
    if not words:
        return []
    
    freq = Counter(words)
    freq_filtered = {w: c for w, c in freq.items() if c >= min_freq}
    
    return [w for w, _ in sorted(freq_filtered.items(), key=lambda x: -x[1])[:max_keywords]]


def jaccard_similarity(set1, set2):
    union = set1 | set2
    if not union:
        return 0.0
    return len(set1 & set2) / len(union)


def find_related(entries, keywords, threshold=0.3, max_results=5):
    """Find related entries based on keyword Jaccard similarity."""
    new_kws = set(keywords)
    if not new_kws:
        return []
    
    related = []
    for entry in entries:
        existing_kws = set(entry.get("keywords", []))
        jaccard = jaccard_similarity(new_kws, existing_kws)
        
        if jaccard >= threshold:
            related.append(entry["id"])
    
    return related[:max_results]


def auto_detect_type(content, title, keywords):
    """Auto-detect memory type based on content heuristics."""
    text = (title + " " + content + " " + " ".join(keywords)).lower()
    
    longterm_words = [
        "architecture", "design pattern", "convention", "structure",
        "extends", "implements", "base class", "inheritance",
        "api", "interface", "contract", "schema", "data flow",
        "decision", "rationale", "why we", "because",
        "pattern", "journaler", "factory", "singleton"
    ]
    
    transient_words = [
        "fixing", "working on", "task", "todo", "bug", "error",
        "exception", "crash", "debugging", "refactor",
        "currently", "in progress", "wip"
    ]
    
    longterm_score = sum(1 for w in longterm_words if w in text)
    transient_score = sum(1 for w in transient_words if w in text)
    
    if longterm_score > transient_score:
        return "longterm"
    elif transient_score > longterm_score:
        return "transient"
    else:
        return "longterm"


def get_preview(content, max_chars=200):
    if len(content) <= max_chars:
        return content
    preview = content[:max_chars]
    last_space = preview.rfind(' ')
    if last_space > max_chars * 0.7:
        preview = preview[:last_space]
    return preview + "..."


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
                raise TimeoutError(f"Lock timeout after {timeout}s")
            time.sleep(0.1)


def release_lock(fd):
    """Release file lock."""
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()
