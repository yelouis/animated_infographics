"""Gate lock wrapper for animated_infographics gate scripts per design_system_architecture.md §11.

Ensures gates never run concurrently across the machine.
Usage:
    python -m animated_infographics.gatelock <name> -- <command...>
"""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys

from animated_infographics.memguard import get_lock_dir


def is_live_ancestor(pid: int) -> bool:
    """Check if pid is a live ancestor of the current process."""
    if pid <= 1 or pid == os.getpid():
        return False
    curr = os.getppid()
    while curr > 1:
        if curr == pid:
            return True
        try:
            res = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(curr)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                break
            out = res.stdout.strip()
            if not out:
                break
            curr = int(out)
        except Exception:
            break
    return False


def run_gatelock(name: str, command: list[str]) -> int:
    """Run command under gate.lock mutual exclusion per §11."""
    if not command:
        print("error: gatelock requires a command to execute", file=sys.stderr)
        return 1

    # Check if an ancestor process already holds the gate lock
    held_env = os.environ.get("INFOGRAPHICS_GATE_LOCK_HELD")
    if held_env:
        try:
            held_pid = int(held_env.strip())
            if is_live_ancestor(held_pid):
                # Nested gate call under ancestor holder: run command directly
                res = subprocess.run(command)
                return res.returncode
        except (ValueError, TypeError):
            pass

    lock_dir = get_lock_dir()
    lock_file = lock_dir / "gate.lock"

    try:
        lock_fd = open(lock_file, "a+", encoding="utf-8")
    except OSError as e:
        print(f"error opening gate lock file {lock_file}: {e}", file=sys.stderr)
        return 1

    try:
        # Non-blocking exclusive flock
        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        # Lock is held by another process
        holder_info = "unknown"
        try:
            lock_fd.seek(0)
            content = lock_fd.read().strip()
            if content:
                holder_info = content
        except Exception:
            pass
        print(f"another gate is running: {holder_info}")
        lock_fd.close()
        return 3

    # Lock acquired: record holder info
    try:
        lock_fd.seek(0)
        lock_fd.truncate()
        lock_fd.write(f"{name} pid {os.getpid()}\n")
        lock_fd.flush()

        env = os.environ.copy()
        env["INFOGRAPHICS_GATE_LOCK_HELD"] = str(os.getpid())

        res = subprocess.run(command, env=env)
        return res.returncode
    finally:
        try:
            lock_fd.seek(0)
            lock_fd.truncate()
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(
            "usage: python -m animated_infographics.gatelock <name> -- <command...>",
            file=sys.stderr,
        )
        sys.exit(1)

    name = args[0]
    rest = args[1:]

    if "--" in rest:
        sep_idx = rest.index("--")
        command = rest[sep_idx + 1 :]
    else:
        command = rest

    code = run_gatelock(name, command)
    sys.exit(code)


if __name__ == "__main__":
    main()
