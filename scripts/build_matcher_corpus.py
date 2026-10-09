#!/usr/bin/env python3
"""Build and freeze the 8-job presentation matcher corpus for Wave J.

Per design_presentation_simulation.md §6.6.3 and agent_execution_guide.md §1.3 (J1).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from animated_infographics.evals.asset_health import execution_errors

HASH_FILES = [
    "deck.json",
    "tree.json",
    "performance.json",
    "speak_timing.json",
    "heard.json",
]

CONFIGS = [
    # Decision set (seed 7)
    {
        "fixture": "fixtures/scripts/history_great_stink.txt",
        "tag": "history_great_stink",
        "style": "literal",
        "perturb": "mild",
        "seed": 7,
    },
    {
        "fixture": "fixtures/scripts/history_great_stink.txt",
        "tag": "history_great_stink",
        "style": "creative",
        "perturb": "strong",
        "seed": 7,
    },
    {
        "fixture": "fixtures/scripts/story_overdue_book.txt",
        "tag": "story_overdue_book",
        "style": "literal",
        "perturb": "strong",
        "seed": 7,
    },
    {
        "fixture": "fixtures/scripts/story_overdue_book.txt",
        "tag": "story_overdue_book",
        "style": "creative",
        "perturb": "mild",
        "seed": 7,
    },
    # Held-out set (seed 11)
    {
        "fixture": "fixtures/scripts/history_great_stink.txt",
        "tag": "history_great_stink",
        "style": "literal",
        "perturb": "mild",
        "seed": 11,
    },
    {
        "fixture": "fixtures/scripts/history_great_stink.txt",
        "tag": "history_great_stink",
        "style": "creative",
        "perturb": "strong",
        "seed": 11,
    },
    {
        "fixture": "fixtures/scripts/story_overdue_book.txt",
        "tag": "story_overdue_book",
        "style": "literal",
        "perturb": "strong",
        "seed": 11,
    },
    {
        "fixture": "fixtures/scripts/story_overdue_book.txt",
        "tag": "story_overdue_book",
        "style": "creative",
        "perturb": "mild",
        "seed": 11,
    },
]


def run_cmd(cmd: list[str], env: dict[str, str]) -> str:
    print(f"--> Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}", file=sys.stderr)
        print(f"STDOUT:\n{res.stdout}", file=sys.stderr)
        print(f"STDERR:\n{res.stderr}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.stdout


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    corpus_dir = repo_root / "artifacts" / "matcher_bakeoff" / "2026-10-09" / "corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if "HF_HOME" not in env or not (Path(env["HF_HOME"]) / "hub").is_dir():
        env["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

    jobs_summary = []

    for idx, cfg in enumerate(CONFIGS, 1):
        print("\n==================================================")
        print(
            f"Building job {idx}/8: {cfg['tag']} style={cfg['style']} "
            f"perturb={cfg['perturb']} seed={cfg['seed']}"
        )
        print("==================================================")

        # 1. Run present-sim
        sim_cmd = [
            "uv",
            "run",
            "infographics",
            "present-sim",
            cfg["fixture"],
            "--style",
            cfg["style"],
            "--perturb",
            cfg["perturb"],
            "--seed",
            str(cfg["seed"]),
            "--matcher",
            "bm25",
            "--jobs-dir",
            str(corpus_dir),
        ]
        out_sim = run_cmd(sim_cmd, env)

        # Find job_id
        m = re.search(r"job_id:\s*(\S+)", out_sim)
        if not m:
            print(f"[-] Could not find job_id in output:\n{out_sim}", file=sys.stderr)
            sys.exit(1)
        job_id = m.group(1).strip()
        job_dir = corpus_dir / job_id

        # 2. Score job
        score_cmd = [
            "uv",
            "run",
            "infographics",
            "score",
            job_id,
            "--jobs-dir",
            str(corpus_dir),
        ]
        run_cmd(score_cmd, env)

        # 3. Check each job invariants
        # 3a. 0 asset execution errors
        asset_errors = execution_errors(job_dir)
        if asset_errors:
            print(f"[-] Asset execution errors in {job_id}: {asset_errors}", file=sys.stderr)
            sys.exit(1)
        print(f"[+] 0 asset execution errors in {job_id}")

        # 3b. Creative jobs not degraded, director.json present
        if cfg["style"] == "creative":
            tree_path = job_dir / "tree.json"
            if not tree_path.is_file():
                print(f"[-] Missing tree.json in {job_id}", file=sys.stderr)
                sys.exit(1)
            tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
            if tree_data.get("style_degraded"):
                print(f"[-] Creative job {job_id} degraded to literal!", file=sys.stderr)
                sys.exit(1)
            director_path = job_dir / "director.json"
            if not director_path.is_file():
                print(f"[-] Missing director.json in creative job {job_id}", file=sys.stderr)
                sys.exit(1)
            print(f"[+] Creative job {job_id} sound: not degraded, director.json present")

        # 4. Compute file hashes
        hashes = {}
        for fname in HASH_FILES:
            fpath = job_dir / fname
            if not fpath.is_file():
                print(f"[-] Required corpus file {fname} missing in {job_id}", file=sys.stderr)
                sys.exit(1)
            h = hashlib.sha256(fpath.read_bytes()).hexdigest()
            hashes[fname] = h

        jobs_summary.append(
            {
                "job_id": job_id,
                "fixture": cfg["tag"],
                "style": cfg["style"],
                "perturb": cfg["perturb"],
                "seed": cfg["seed"],
                "hashes": hashes,
            }
        )

    # Write corpus.json
    corpus_json_path = corpus_dir / "corpus.json"
    corpus_record = {
        "corpus_version": 1,
        "date": "2026-10-09",
        "description": "Frozen 8-job corpus for Wave J matcher bake-off",
        "jobs": jobs_summary,
    }
    corpus_json_path.write_text(json.dumps(corpus_record, indent=2) + "\n", encoding="utf-8")
    print(f"\n[+] Successfully froze 8-job corpus to {corpus_json_path}")


if __name__ == "__main__":
    main()
