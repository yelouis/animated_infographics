"""Verification of creative style bars across rendered E2E jobs.

Per design_styles.md §3.7 and design_testing_and_validation.md §4b:
- Every motif has >= 1 plant rendered (as a token) before its payoff rendered (as a callback).
- >= 2 metaphor scenes rendered.
- >= 2 asides rendered.
- 0 license failures left (no items that failed license check are rendered).
- 0 overlay/slot overlaps (allowed templates only, capacity <= 1 token & <= 1 aside).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from animated_infographics.contracts.templates import ALLOWED_OVERLAY_TEMPLATES


def verify_job_creative(job_dir: Path | str) -> dict[str, Any]:
    """Verify creative bars for a single rendered job directory."""
    p = Path(job_dir)
    timeline_path = p / "timeline.json"
    director_path = p / "director.json"
    report_path = p / "preview" / "report.json"

    if not timeline_path.is_file():
        raise FileNotFoundError(f"Missing timeline.json in {job_dir}")

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    scenes = timeline.get("scenes", [])

    director_data: dict[str, Any] = {}
    if director_path.is_file():
        try:
            director_data = json.loads(director_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    report_items: list[dict[str, Any]] = []
    if report_path.is_file():
        try:
            r_json = json.loads(report_path.read_text(encoding="utf-8"))
            report_items = r_json.get("director_items", [])
        except Exception:
            pass

    valid_fates = {"rendered", "moved", "license_dropped", "overlay_dropped"}
    invalid_fates = [it for it in report_items if it.get("fate") not in valid_fates]

    # 1. Metaphor scenes count
    metaphor_scenes = [s for s in scenes if s.get("template") == "metaphor"]
    metaphors_count = len(metaphor_scenes)

    # 2. Asides count (thought, label, prop overlays)
    asides_count = 0
    motif_tokens_by_scene: list[tuple[int, str]] = []  # (scene_idx, motif_id)
    for idx, sc in enumerate(scenes):
        for ov in sc.get("overlays", []):
            k = ov.get("kind")
            if k in ("thought", "label", "prop"):
                asides_count += 1
            elif k == "motif_token":
                motif_tokens_by_scene.append((idx, ov.get("motif_id", "")))

    # 3. Payoffs and plants
    # Every motif with a rendered payoff (callback) must have >= 1 plant rendered before it
    callback_scenes = [s for s in scenes if s.get("template") == "callback"]
    payoffs_count = len(callback_scenes)
    unplanted_payoffs: list[str] = []

    for cb in callback_scenes:
        m_id = cb.get("props", {}).get("motif_id")
        cb_idx = next((i for i, s in enumerate(scenes) if s.get("id") == cb.get("id")), -1)
        # Find earlier motif tokens with this motif_id
        plants_before = [
            idx
            for (idx, token_m_id) in motif_tokens_by_scene
            if token_m_id == m_id and idx < cb_idx
        ]
        if not plants_before:
            unplanted_payoffs.append(f"{cb.get('id')}:{m_id}")

    # Total motifs rendered: motifs that have at least a payoff or a token
    cb_motif_ids = [
        cb.get("props", {}).get("motif_id")
        for cb in callback_scenes
        if cb.get("props", {}).get("motif_id")
    ]
    motifs_rendered = len(set(cb_motif_ids + [t[1] for t in motif_tokens_by_scene if t[1]]))

    # 4. License check: 0 items left that failed the license check
    license_failures_rendered = 0
    license_dropped = director_data.get("license_dropped", [])
    # Check if any dropped item somehow ended up in timeline
    for ld in license_dropped:
        item = ld.get("item", {})
        beat_i = item.get("beat_i")
        kind = item.get("kind")
        if beat_i is not None and 0 <= beat_i < len(scenes):
            sc = scenes[beat_i]
            if kind == "metaphor" or "image" in item:
                if sc.get("template") == "metaphor":
                    license_failures_rendered += 1
            elif kind in ("thought", "label", "prop"):
                if any(o.get("kind") == kind for o in sc.get("overlays", [])):
                    license_failures_rendered += 1

    # 5. Overlays clearance / overlaps:
    # Overlays only on ALLOWED_OVERLAY_TEMPLATES, at most 1 token and 1 aside per scene
    overlay_violations = 0
    for sc in scenes:
        ovs = sc.get("overlays", [])
        if not ovs:
            continue
        tmpl = sc.get("template", "")
        if tmpl not in ALLOWED_OVERLAY_TEMPLATES:
            overlay_violations += 1
        tokens = [o for o in ovs if o.get("kind") == "motif_token"]
        asides = [o for o in ovs if o.get("kind") in ("thought", "label", "prop")]
        if len(tokens) > 1 or len(asides) > 1:
            overlay_violations += 1

    # Bars:
    # - >= 1 motif with plant & payoff rendered
    # - unplanted_payoffs == 0
    # - >= 2 metaphors
    # - >= 2 asides
    # - 0 license failures rendered
    # - 0 overlay violations
    motifs_bar = motifs_rendered >= 1 and payoffs_count >= 1 and len(unplanted_payoffs) == 0
    metaphors_bar = metaphors_count >= 2
    asides_bar = asides_count >= 2
    license_bar = license_failures_rendered == 0
    overlays_bar = overlay_violations == 0
    fates_bar = len(invalid_fates) == 0

    all_passed = (
        motifs_bar and metaphors_bar and asides_bar and license_bar and overlays_bar and fates_bar
    )

    job_label = p.name if p.is_dir() else p.parent.name
    return {
        "job": job_label,
        "motifs_rendered": motifs_rendered,
        "payoffs_rendered": payoffs_count,
        "unplanted_payoffs": unplanted_payoffs,
        "metaphors_count": metaphors_count,
        "asides_count": asides_count,
        "license_failures_rendered": license_failures_rendered,
        "overlay_violations": overlay_violations,
        "invalid_fates_count": len(invalid_fates),
        "motifs_bar": motifs_bar,
        "metaphors_bar": metaphors_bar,
        "asides_bar": asides_bar,
        "license_bar": license_bar,
        "overlays_bar": overlays_bar,
        "passed": all_passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify creative style bars per design_styles.md §3.7"
    )
    parser.add_argument("jobs", nargs="+", type=Path, help="Job directories to check")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    any_failed = False

    header = (
        f"{'Job':<28} | {'Motifs':<8} | {'Payoffs':<8} | {'Metaphors':<10} | "
        f"{'Asides':<8} | {'LicFail':<8} | {'Overlaps':<8} | {'Status':<6}"
    )
    print(header)
    print("-" * len(header))

    for job_path in args.jobs:
        if not job_path.is_dir() or not (job_path / "timeline.json").exists():
            print(f"Skipping {job_path}: not a valid job dir", file=sys.stderr)
            any_failed = True
            continue

        res = verify_job_creative(job_path)
        results.append(res)
        status = "PASS" if res["passed"] else "FAIL"
        if not res["passed"]:
            any_failed = True

        row = (
            f"{res['job']:<28} | "
            f"{res['motifs_rendered']:<8} | "
            f"{res['payoffs_rendered']:<8} | "
            f"{res['metaphors_count']:<10} | "
            f"{res['asides_count']:<8} | "
            f"{res['license_failures_rendered']:<8} | "
            f"{res['overlay_violations']:<8} | "
            f"{status:<6}"
        )
        print(row)

    if any_failed:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
