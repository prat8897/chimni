"""Run generated code in a child process with limits.

What the sandbox does:
  - a fresh empty temp directory as the working directory, deleted afterwards
  - `python -I` (no user site-packages, no PYTHON* env vars, script dir not on sys.path) and a minimal environment
  - CPU-time, file-size and process limits (setrlimit), an address-space limit on Linux, and a wall-clock timeout
  - no network: `unshare -rn` on Linux, `sandbox-exec` with a deny-network profile on macOS, when available

If no network isolation mechanism works on this machine, runs still happen but every result records
`network_isolation: "none"`, and the report says so. This is a guard against accidents, not against a
determined adversary.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from .common import CHIMNI_SRC

HARNESS = Path(__file__).resolve().parent / "harness.py"
WALL_TIMEOUT = 30          # seconds for a whole batch of ~300 inputs
CPU_SECONDS = 20
MEMORY_BYTES = 4 * 1024 ** 3
MAC_PROFILE = "(version 1)(allow default)(deny network*)"


def _limits():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 ** 2, 10 * 1024 ** 2))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
    os.setsid()


@lru_cache(maxsize=None)
def network_isolation():
    """Return (name, argv prefix) for the first mechanism that works here."""
    candidates = []
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        candidates.append(("sandbox-exec", ["sandbox-exec", "-p", MAC_PROFILE]))
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        candidates.append(("unshare", ["unshare", "-rn"]))
    for name, prefix in candidates:
        try:
            ok = subprocess.run(prefix + [sys.executable, "-c", "pass"], capture_output=True, timeout=20).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
        if ok:
            return name, tuple(prefix)
    return "none", ()


def run_solution(lang, code, inputs, tables=None, sql_output=None, timeout=WALL_TIMEOUT):
    """Run `code` on every input. Returns the harness result plus `network_isolation`,
    or {"status": "timeout"} / {"status": "crash", "message": ...}."""
    iso_name, prefix = network_isolation()
    with tempfile.TemporaryDirectory(prefix="chimni-bench-") as tmp:
        job = Path(tmp) / "job.json"
        job.write_text(json.dumps({"lang": lang, "code": code, "inputs": inputs, "tables": tables or {},
                                   "sql_output": sql_output, "chimni_src": str(CHIMNI_SRC)}), encoding="utf-8")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tmp, "LANG": "C.UTF-8",
               "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
        argv = list(prefix) + [sys.executable, "-I", str(HARNESS), str(job)]
        try:
            p = subprocess.run(argv, cwd=tmp, env=env, capture_output=True, text=True, timeout=timeout,
                               preexec_fn=_limits)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "network_isolation": iso_name}
    if p.returncode != 0 or not p.stdout.strip():
        if p.returncode in (-24, -9) or "SIGXCPU" in p.stderr:     # CPU limit
            return {"status": "timeout", "network_isolation": iso_name}
        tail = (p.stderr or "").strip().splitlines()[-3:]
        return {"status": "crash", "message": f"exit code {p.returncode}: " + " | ".join(tail),
                "network_isolation": iso_name}
    out = json.loads(p.stdout.strip().splitlines()[-1])
    out["network_isolation"] = iso_name
    return out
