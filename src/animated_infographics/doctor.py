"""Health check and dependency verification for Animated Infographics.

Checks toolchains, models, fonts, geodata, and caches.
Exits 0 if all checks pass, exit 4 if any check fails.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

import httpx
from huggingface_hub import scan_cache_dir, try_to_load_from_cache

from animated_infographics.memguard import (
    FLOOR,
    HEAVY_STEPS,
    get_heavy_lock_holder,
    read_memory,
)

# HF repo id for FLUX.2 klein 4B used by mflux
FLUX2_KLEIN_4B_REPO: Final[str] = "black-forest-labs/FLUX.2-klein-4B"

# Relative path patterns for Remotion headless browser installed by 'remotion browser ensure'.
# Remotion searches up the directory hierarchy for node_modules/.remotion/chrome-headless-shell/.
REMOTION_BROWSER_PATHS: Final[list[str]] = [
    "renderer/node_modules/.remotion/chrome-headless-shell",
    "../node_modules/.remotion/chrome-headless-shell",
]

REQUIRED_FONTS: Final[list[str]] = [
    "Poppins-Bold.ttf",
    "Poppins-ExtraBold.ttf",
    "Inter-Medium.ttf",
    "Inter-SemiBold.ttf",
    "Inter-Bold.ttf",
]


def get_project_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(4):
        if (cur / "pyproject.toml").is_file():
            return cur
        cur = cur.parent
    return Path.cwd()


def check_hf_file(repo_id: str, filename: str) -> bool:
    try:
        res = try_to_load_from_cache(repo_id, filename)
        return res is not None and isinstance(res, str) and Path(res).is_file()
    except Exception:
        return False


def check_hf_repo(repo_id: str) -> bool:
    try:
        scan = scan_cache_dir()
        for repo in scan.repos:
            if repo.repo_id == repo_id:
                return True
        return False
    except Exception:
        return False


def verify_vendor_checksums(vendor_dir: Path, checksums_path: Path) -> tuple[bool, str]:
    if not checksums_path.is_file():
        return False, "data/vendor/CHECKSUMS missing"
    try:
        content = checksums_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            expected_hash, rel_name = parts[0], parts[1].strip()
            target_file = vendor_dir / rel_name
            if not target_file.is_file():
                return False, f"vendor file missing: {rel_name}"
            actual_hash = hashlib.sha256(target_file.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                return False, f"hash mismatch for {rel_name}"
        return True, ""
    except Exception as exc:
        return False, str(exc)


def check_remotion_browser(project_root: Path) -> bool:
    for rel_path in REMOTION_BROWSER_PATHS:
        browser_root = (project_root / rel_path).resolve()
        if not browser_root.is_dir():
            continue
        for path in browser_root.rglob("chrome-headless-shell"):
            if path.is_file() and os.access(path, os.X_OK):
                return True
    return False


def run_doctor() -> int:
    project_root = get_project_root()
    missing_count = 0

    def report_ok(label: str) -> None:
        print(f"OK   {label}")

    def report_missing(label: str, fix: str) -> None:
        nonlocal missing_count
        missing_count += 1
        print(f"MISSING {label} — run: {fix}")

    # 1. Python 3.12
    v = sys.version_info
    if v.major == 3 and v.minor == 12:
        report_ok(f"Python 3.12 ({v.major}.{v.minor}.{v.micro})")
    else:
        report_missing(f"Python 3.12 (found {v.major}.{v.minor})", "uv python install 3.12")

    # 2. ffmpeg
    if shutil.which("ffmpeg"):
        report_ok("ffmpeg")
    else:
        report_missing("ffmpeg", "brew install ffmpeg")

    # 3. ffprobe
    if shutil.which("ffprobe"):
        report_ok("ffprobe")
    else:
        report_missing("ffprobe", "brew install ffmpeg")

    # 4. espeak-ng
    if shutil.which("espeak-ng"):
        report_ok("espeak-ng")
    else:
        report_missing("espeak-ng", "brew install espeak-ng")

    # 5. Ollama reachable & planner model present
    planner_model = os.environ.get("INFOGRAPHICS_PLANNER_MODEL", "gemma4:26b")
    try:
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=3.0)
        if resp.status_code == 200:
            report_ok("Ollama reachable at 127.0.0.1:11434")
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            model_match = any(
                m == planner_model
                or m.startswith(f"{planner_model}:")
                or planner_model.startswith(f"{m}:")
                for m in models
            )
            if model_match:
                report_ok(f"planner model '{planner_model}' in Ollama")
            else:
                report_missing(
                    f"planner model '{planner_model}' in Ollama",
                    f"ollama pull {planner_model}",
                )
        else:
            report_missing("Ollama at 127.0.0.1:11434 (bad status)", "ollama serve")
    except Exception:
        report_missing("Ollama at 127.0.0.1:11434", "ollama serve")

    # 6. mflux-generate-flux2 on PATH and supports flux2-klein-4b
    mflux_bin = shutil.which("mflux-generate-flux2")
    if not mflux_bin:
        report_missing("mflux-generate-flux2 on PATH", "uv tool install mflux")
    else:
        try:
            res = subprocess.run(
                [mflux_bin, "--help"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            help_text = res.stdout + " " + res.stderr
            if "flux2-klein-4b" in help_text:
                report_ok("mflux-generate-flux2 on PATH (supports flux2-klein-4b)")
            else:
                report_missing(
                    "mflux-generate-flux2 with flux2-klein-4b support",
                    "uv tool update mflux",
                )
        except Exception as e:
            report_missing(
                "mflux-generate-flux2 with flux2-klein-4b support",
                f"error running mflux-generate-flux2 --help: {e}",
            )

    # 7. In HF cache (Whisper, Kokoro, af_heart, am_michael, klein 4B)
    whisper_repo = "mlx-community/whisper-large-v3-turbo"
    if check_hf_file(whisper_repo, "config.json") or check_hf_repo(whisper_repo):
        report_ok(f"Whisper model {whisper_repo} in HF cache")
    else:
        report_missing(f"Whisper model {whisper_repo} in HF cache", "scripts/setup.sh")

    kokoro_repo = "hexgrad/Kokoro-82M"
    if check_hf_file(kokoro_repo, "config.json") or check_hf_repo(kokoro_repo):
        report_ok(f"Kokoro model {kokoro_repo} in HF cache")
    else:
        report_missing(
            f"Kokoro model {kokoro_repo} in HF cache",
            "scripts/setup.sh (if HF_HOME is set, it must contain "
            "hub/models--hexgrad--Kokoro-82M; unset it or export "
            'HF_HOME="$HOME/.cache/huggingface")',
        )

    if check_hf_file(kokoro_repo, "voices/af_heart.pt"):
        report_ok("Kokoro voice voices/af_heart.pt in HF cache")
    else:
        report_missing("Kokoro voice voices/af_heart.pt in HF cache", "scripts/setup.sh")

    if check_hf_file(kokoro_repo, "voices/am_michael.pt"):
        report_ok("Kokoro voice voices/am_michael.pt in HF cache")
    else:
        report_missing("Kokoro voice voices/am_michael.pt in HF cache", "scripts/setup.sh")

    if check_hf_repo(FLUX2_KLEIN_4B_REPO):
        report_ok(f"FLUX.2 klein 4B weights ({FLUX2_KLEIN_4B_REPO}) in HF cache")
    else:
        report_missing(
            f"FLUX.2 klein 4B weights ({FLUX2_KLEIN_4B_REPO}) in HF cache",
            "scripts/setup.sh",
        )

    # 8. renderer/node_modules
    node_modules_dir = project_root / "renderer" / "node_modules"
    if node_modules_dir.is_dir():
        report_ok("renderer/node_modules")
    else:
        report_missing("renderer/node_modules", "npm --prefix renderer ci")

    # 9. Remotion headless browser
    if check_remotion_browser(project_root):
        report_ok("Remotion headless browser")
    else:
        report_missing(
            "Remotion headless browser",
            "npx --prefix renderer remotion browser ensure",
        )

    # 10. Fonts
    fonts_dir = project_root / "renderer" / "public" / "fonts"
    for font_name in REQUIRED_FONTS:
        font_path = fonts_dir / font_name
        if font_path.is_file() and font_path.stat().st_size > 0:
            report_ok(f"font {font_name}")
        else:
            report_missing(f"font {font_name}", "scripts/setup.sh")

    # 11. data/vendor/* against CHECKSUMS
    vendor_dir = project_root / "data" / "vendor"
    checksums_file = vendor_dir / "CHECKSUMS"
    ok_vendor, vendor_err = verify_vendor_checksums(vendor_dir, checksums_file)
    if ok_vendor:
        report_ok("data/vendor/* verified against CHECKSUMS")
    else:
        report_missing(f"data/vendor/* ({vendor_err})", "scripts/setup.sh")

    # 12. data/geo/country_bboxes.json
    bboxes_file = project_root / "data" / "geo" / "country_bboxes.json"
    if bboxes_file.is_file() and bboxes_file.stat().st_size > 100:
        report_ok("data/geo/country_bboxes.json")
    else:
        report_missing(
            "data/geo/country_bboxes.json",
            "npx --prefix renderer tsx renderer/scripts/gen-country-bboxes.ts",
        )

    # 13. renderer/public/geo/lakes-50m.json
    lakes_file = project_root / "renderer" / "public" / "geo" / "lakes-50m.json"
    if lakes_file.is_file() and lakes_file.stat().st_size > 100:
        report_ok("renderer/public/geo/lakes-50m.json")
    else:
        report_missing(
            "renderer/public/geo/lakes-50m.json",
            "npx --prefix renderer tsx renderer/scripts/gen-lakes.ts",
        )

    # 14. Hardware memory check per §11:
    # Fails (exit 4) if hw.memsize < largest declared peak + llm_load + FLOOR
    largest_peak = max(HEAVY_STEPS.values())
    llm_peak = HEAVY_STEPS.get("llm_load", 12 * (1024**3))
    min_required_bytes = largest_peak + llm_peak + FLOOR
    min_required_gb = min_required_bytes // (1024**3)

    hw_memsize = 0
    try:
        hw_memsize = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    except Exception:
        try:
            hw_memsize = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except Exception:
            hw_memsize = 0

    hw_mem_gb = hw_memsize / (1024**3)
    if hw_memsize >= min_required_bytes:
        report_ok(f"hardware memory ({hw_mem_gb:.0f} GB >= {min_required_gb} GB required)")
    else:
        report_missing(
            f"hardware memory ({hw_mem_gb:.0f} GB < {min_required_gb} GB required)",
            "64 GB unified memory machine",
        )

    # 15. Memory status and lock state per §11
    avail_bytes, pressure = read_memory()
    avail_gb = avail_bytes / (1024**3)
    holder_pid = get_heavy_lock_holder()
    if holder_pid is not None:
        holder_str = f", heavy.lock held by pid {holder_pid}"
    else:
        holder_str = ", heavy.lock free"
    report_ok(f"available memory ({avail_gb:.1f} GB, pressure level {pressure}{holder_str})")

    # Warning (not failure) if available memory < flux + FLOOR right now
    flux_floor_bytes = HEAVY_STEPS.get("flux", 32 * (1024**3)) + FLOOR
    flux_floor_gb = flux_floor_bytes / (1024**3)
    if avail_bytes < flux_floor_bytes:
        print(
            f"WARN available memory ({avail_gb:.1f} GB) is below flux + FLOOR "
            f"({flux_floor_gb:.0f} GB)"
        )

    if missing_count > 0:
        return 4
    return 0


def main() -> None:
    code = run_doctor()
    sys.exit(code)


if __name__ == "__main__":
    main()
