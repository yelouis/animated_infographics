"""Memory guard for admission control and runtime watchdog per design_system_architecture.md §11."""

from __future__ import annotations

import fcntl
import logging
import os
import subprocess
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Final

import httpx

logger = logging.getLogger("animated_infographics.memguard")

# ---------------------------------------------------------------------------
# Exceptions & Constants per §11
# ---------------------------------------------------------------------------


class ResourceUnavailable(Exception):
    """Raised when memory guard cannot admit a heavy step within the time limit or stops it."""

    pass


FLOOR: Final[int] = 8 * (1024**3)  # 8 GB floor

HEAVY_STEPS: Final[dict[str, int]] = {
    # Measured on story_overdue_book October 10, 2026, × 1.15 rounded up to GB
    "flux": 32 * (1024**3),  # 32 GB (measured 27.54 GB × 1.15 rounded up)
    "whisper": 5 * (1024**3),  # 5 GB (measured 4.27 GB × 1.15 rounded up)
    "kokoro": 3 * (1024**3),  # 3 GB (measured 2.42 GB × 1.15 rounded up)
    "render": 6 * (1024**3),  # 6 GB (measured 5.16 GB × 1.15 rounded up)
    "llm_load": 12 * (1024**3),  # 12 GB (llama-server 10.5 GB resident × 1.15)
}

DEFAULT_MEM_WAIT_S: Final[float] = 1800.0
WATCH_POLL_INTERVAL_S: float = 2.0

CURRENT_STAGE_LOG: ContextVar[Path | None] = ContextVar("CURRENT_STAGE_LOG", default=None)


# ---------------------------------------------------------------------------
# Memory reader
# ---------------------------------------------------------------------------


def read_memory() -> tuple[int, int]:
    """Read available memory in bytes and pressure level from macOS kernel.

    Formula per design_system_architecture.md §11:
    available = hw.memsize * kern.memorystatus_level / 100
    pressure_level = kern.memorystatus_vm_pressure_level (1 normal, 2 warning, 4 critical)
    """
    out = subprocess.check_output(
        [
            "sysctl",
            "-n",
            "hw.memsize",
            "kern.memorystatus_level",
            "kern.memorystatus_vm_pressure_level",
        ],
        text=True,
    ).split()
    try:
        memsize = int(out[0])
        level = int(out[1])
        pressure = int(out[2])
        available_bytes = int(memsize * level / 100)
        return available_bytes, pressure
    except (ValueError, IndexError):
        return (64 * (1024**3), 1)


def get_lock_dir() -> Path:
    """Return directory for heavy and gate locks."""
    lock_dir_str = os.environ.get("INFOGRAPHICS_LOCK_DIR")
    if lock_dir_str:
        lock_dir = Path(lock_dir_str)
    else:
        lock_dir = Path.home() / ".cache" / "animated_infographics" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    return lock_dir


@contextmanager
def stage_log_context(log_path: Path) -> Iterator[None]:
    """Context manager setting active stage log path for memguard logging."""
    token = CURRENT_STAGE_LOG.set(log_path)
    try:
        yield
    finally:
        CURRENT_STAGE_LOG.reset(token)


def record_admission(
    step: str,
    waited_ms: int,
    available_gb: float,
    unloaded_llm: bool,
    *,
    log_file: Path | None = None,
) -> None:
    unloaded_str = str(unloaded_llm).lower()
    line = (
        f"memguard step={step} waited_ms={waited_ms} "
        f"available_gb={available_gb:.1f} unloaded_llm={unloaded_str}\n"
    )
    logger.info("Admitted heavy step: %s", line.strip())
    target = log_file or CURRENT_STAGE_LOG.get()
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8") as f:
            f.write(line)


# ---------------------------------------------------------------------------
# Ollama Model Management
# ---------------------------------------------------------------------------

OLLAMA_ENDPOINT: str = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


def is_ollama_model_loaded(model: str = "gemma4:26b", endpoint: str | None = None) -> bool:
    """Check if model is currently loaded in Ollama via GET /api/ps."""
    base = endpoint or OLLAMA_ENDPOINT
    try:
        resp = httpx.get(f"{base}/api/ps", timeout=5.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return any(
                m.get("name") == model
                or m.get("model") == model
                or (m.get("name") or "").startswith(f"{model}:")
                for m in models
            )
    except Exception:
        pass
    return False


def unload_ollama_model(
    model: str = "gemma4:26b",
    endpoint: str | None = None,
    timeout_s: float = 30.0,
) -> bool:
    """Unload model from Ollama via POST /api/generate with keep_alive: 0."""
    base = endpoint or OLLAMA_ENDPOINT
    try:
        httpx.post(
            f"{base}/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=10.0,
        )
    except Exception as e:
        logger.warning("Failed to request Ollama unload for %s: %s", model, e)
        return False

    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if not is_ollama_model_loaded(model, endpoint=base):
            return True
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# In-process Model Release
# ---------------------------------------------------------------------------


def release_in_process_models() -> None:
    """Drop references, gc.collect(), and clear MLX/MPS caches."""
    import gc
    import sys

    if "mlx_whisper.transcribe" in sys.modules:
        m = sys.modules["mlx_whisper.transcribe"]
        if hasattr(m, "ModelHolder"):
            m.ModelHolder.model = None
            m.ModelHolder.model_path = None

    gc.collect()

    try:
        import mlx.core as mx

        if hasattr(mx, "clear_cache"):
            mx.clear_cache()
        elif hasattr(mx, "metal") and hasattr(mx.metal, "clear_cache"):
            mx.metal.clear_cache()
    except Exception:
        pass

    try:
        import torch

        if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()
    except Exception:
        pass

    gc.collect()


# ---------------------------------------------------------------------------
# Heavy Step Guard
# ---------------------------------------------------------------------------


@contextmanager
def guard(step: str, *, stage_log: Path | str | None = None) -> Iterator[None]:
    """Admission control and heavy step mutual exclusion lock per §11."""
    timeout_s = float(os.environ.get("INFOGRAPHICS_MEM_WAIT_S", str(DEFAULT_MEM_WAIT_S)))
    lock_dir = get_lock_dir()
    lock_file_path = lock_dir / "heavy.lock"
    target_log = Path(stage_log) if stage_log else None

    peak = HEAVY_STEPS.get(step, 0)
    t_start = time.monotonic()

    # 1. Take machine-wide heavy lock (non-blocking poll)
    lock_fd = open(lock_file_path, "a+")
    acquired_lock = False
    try:
        while time.monotonic() - t_start < timeout_s:
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired_lock = True
                try:
                    lock_fd.seek(0)
                    lock_fd.truncate()
                    lock_fd.write(f"{step} pid {os.getpid()}\n")
                    lock_fd.flush()
                except Exception:
                    pass
                break
            except (BlockingIOError, OSError):
                time.sleep(0.05)

        if not acquired_lock:
            raise ResourceUnavailable(
                f"memory guard: timed out waiting {timeout_s}s for heavy lock for {step}"
            )

        # 2. Admission loop
        unloaded_llm = False
        admitted = False
        last_log_time = 0.0

        while time.monotonic() - t_start < timeout_s:
            available, pressure = read_memory()

            if available - peak >= FLOOR:
                admitted = True
                break

            # 3. Unload our own model if that suffices
            if not unloaded_llm and step != "llm_load" and is_ollama_model_loaded("gemma4:26b"):
                if unload_ollama_model("gemma4:26b"):
                    print(
                        f"memory guard: unloaded gemma4:26b to admit {step}",
                        flush=True,
                    )
                    logger.info("memory guard: unloaded gemma4:26b to admit %s", step)
                    unloaded_llm = True
                    # Re-check available memory immediately
                    available, pressure = read_memory()
                    if available - peak >= FLOOR:
                        admitted = True
                        break

            # 4. Otherwise wait
            now = time.monotonic()
            if now - last_log_time >= 30.0:
                avail_gb = available / (1024**3)
                peak_gb = peak / (1024**3)
                print(
                    f"memory guard: waiting for {step}: need {peak_gb:.0f} GB + floor 8 GB, "
                    f"available {avail_gb:.1f} GB",
                    flush=True,
                )
                logger.info(
                    "memory guard: waiting for %s: need %.0f GB + floor 8 GB, available %.1f GB",
                    step,
                    peak_gb,
                    avail_gb,
                )
                last_log_time = now

            # Sleep 5s (or smaller if close to timeout)
            time.sleep(5.0)

        if not admitted:
            avail_gb = available / (1024**3)
            peak_gb = peak / (1024**3)
            raise ResourceUnavailable(
                f"memory guard: timed out waiting {timeout_s}s for {step}: "
                f"need {peak_gb:.0f} GB + floor 8 GB, available {avail_gb:.1f} GB"
            )

        waited_ms = int((time.monotonic() - t_start) * 1000)
        # If admitted without loop wait, waited_ms is 0
        if waited_ms < 50:
            waited_ms = 0
        avail_gb = available / (1024**3)
        record_admission(
            step,
            waited_ms,
            avail_gb,
            unloaded_llm,
            log_file=target_log,
        )

        yield

    finally:
        if acquired_lock:
            try:
                lock_fd.seek(0)
                lock_fd.truncate()
            except Exception:
                pass
            try:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        try:
            lock_fd.close()
        except Exception:
            pass


def get_heavy_lock_holder() -> int | None:
    """Read holder PID of heavy.lock if currently held, else None."""
    lock_file = get_lock_dir() / "heavy.lock"
    if not lock_file.exists():
        return None
    try:
        with open(lock_file, "r+", encoding="utf-8") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return None  # not held
            except (BlockingIOError, OSError):
                # Held! Read PID
                content = f.read().strip()
                parts = content.split()
                if "pid" in parts:
                    idx = parts.index("pid")
                    if idx + 1 < len(parts):
                        return int(parts[idx + 1])
                for p in parts:
                    if p.isdigit():
                        return int(p)
                return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Watchdog for running subprocesses
# ---------------------------------------------------------------------------


@contextmanager
def watch(step: str, popen: subprocess.Popen) -> Iterator[None]:
    """Runtime memory watchdog monitoring subprocesses per §11."""
    stop_event = threading.Event()
    stopped_info: dict[str, Any] = {}

    def _monitor() -> None:
        while not stop_event.is_set():
            if popen.poll() is not None:
                break
            if stop_event.wait(WATCH_POLL_INTERVAL_S):
                break
            if popen.poll() is not None:
                break

            try:
                available, pressure = read_memory()
            except Exception:
                continue

            if pressure >= 4 or available < (FLOOR // 2):
                stopped_info["stopped"] = True
                stopped_info["available_gb"] = available / (1024**3)
                logger.warning(
                    "memory guard: critical pressure (%d) or low memory (%.1f GB), "
                    "stopping %s (pid %d)",
                    pressure,
                    stopped_info["available_gb"],
                    step,
                    popen.pid,
                )
                try:
                    popen.terminate()
                    t_term = time.monotonic()
                    while time.monotonic() - t_term < 10.0:
                        if popen.poll() is not None:
                            break
                        time.sleep(0.5)
                    if popen.poll() is None:
                        popen.kill()
                except Exception:
                    pass
                break

    monitor_thread = threading.Thread(target=_monitor, daemon=True)
    monitor_thread.start()

    try:
        yield
    finally:
        stop_event.set()
        monitor_thread.join(timeout=1.0)
        if stopped_info.get("stopped"):
            avail_gb = stopped_info.get("available_gb", 0.0)
            raise ResourceUnavailable(
                f"memory guard: stopped {step} at {avail_gb:.1f} GB available"
            )
