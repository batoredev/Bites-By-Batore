"""One clean-browser helper per worker process, bounded and restarted after failure."""

import atexit
import json
import queue
import subprocess
import sys
import threading
import time
from .providers import Unavailable


class BrowserHost:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.output = queue.Queue()
        self.last_used = 0
        self.idle_timer = None

    def close(self):
        if self.idle_timer is not None:
            self.idle_timer.cancel()
            self.idle_timer = None
        if self.process is not None:
            process, self.process = self.process, None
            try:
                process.stdin.close()
                process.wait(timeout=2)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                process.kill()
                process.wait(timeout=5)

    def request(self, url, seconds):
        with self.lock:
            if self.process is not None and (
                self.process.poll() is not None or time.monotonic() - self.last_used > 120
            ):
                self.close()
            if self.process is None:
                self.output = queue.Queue()
                self.process = subprocess.Popen(
                    [sys.executable, "-m", "app.browser_sources", "--serve"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                process, output = self.process, self.output

                def read():
                    try:
                        while line := process.stdout.readline(150001):
                            if len(line) > 150000:
                                output.put(None)
                                return
                            output.put(line)
                    finally:
                        output.put(None)

                threading.Thread(target=read, name="batore-browser-output", daemon=True).start()
            try:
                self.process.stdin.write(json.dumps({"url": url, "seconds": seconds}) + "\n")
                self.process.stdin.flush()
                line = self.output.get(timeout=seconds + 20)
                if not line:
                    raise ValueError("Browser helper stopped")
                result = json.loads(line)
                if not isinstance(result, dict) or not isinstance(result.get("browser"), dict):
                    raise ValueError("Browser returned invalid result")
                self.last_used = time.monotonic()
                if self.idle_timer is not None:
                    self.idle_timer.cancel()

                def expire():
                    with self.lock:
                        if time.monotonic() - self.last_used >= 120:
                            self.close()

                self.idle_timer = threading.Timer(120, expire)
                self.idle_timer.daemon = True
                self.idle_timer.start()
                return result
            except (OSError, ValueError, queue.Empty) as exc:
                self.close()
                raise Unavailable("Browser helper unavailable or exceeded its time limit") from exc


HOST = BrowserHost()
atexit.register(HOST.close)
