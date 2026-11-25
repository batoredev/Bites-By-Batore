"""Keep the graphify knowledge graph current without anyone remembering to.

Run by the Claude Code Stop hook (.claude/settings.json) at the end of every turn.
If any code file is newer than graphify-out/graph.json, it starts `graphify update .`
in the background (AST only, no LLM cost) and returns at once. A lock file stops two
rebuilds from overlapping. Commits and checkouts are covered separately by graphify's
own git hooks; doc changes still need `/graphify --update`.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / "graphify-out" / "graph.json"
LOCK = ROOT / "graphify-out" / ".refresh.lock"
LOG = ROOT / "graphify-out" / "refresh.log"
CODE_DIRS = ("backend/app", "backend/tests", "web/src", "web/tests", "scripts")
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".mjs", ".ps1"}
STALE_LOCK_SECONDS = 15 * 60


def newest_code_change() -> float:
    newest = 0.0
    for folder in CODE_DIRS:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix in CODE_EXT and "node_modules" not in path.parts and "__pycache__" not in path.parts:
                newest = max(newest, path.stat().st_mtime)
    return newest


def main() -> int:
    if not GRAPH.exists():
        return 0  # no graph yet: the first build is a deliberate /graphify run
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < STALE_LOCK_SECONDS:
        return 0  # a rebuild is already running
    if newest_code_change() <= GRAPH.stat().st_mtime:
        return 0  # graph already current
    exe = shutil.which("graphify") or str(Path.home() / ".local" / "bin" / "graphify.exe")
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    # Rebuild, then drop the lock; detached so the hook returns immediately.
    script = (
        "import subprocess, pathlib;"
        f"log = open(r'{LOG}', 'a', encoding='utf-8');"
        f"subprocess.run([r'{exe}', 'update', '.'], cwd=r'{ROOT}', stdout=log, stderr=log);"
        f"pathlib.Path(r'{LOCK}').unlink(missing_ok=True)"
    )
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, "-c", script], cwd=ROOT, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
