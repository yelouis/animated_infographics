import json
import shutil
import subprocess
from pathlib import Path


def get_pixel_luma(mp4_path: Path, frame_idx: int) -> int:
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        str(mp4_path),
        "-vf",
        f"select=eq(n\\,{frame_idx}),format=gray,crop=w=1:h=1:x=24:y=24",
        "-vframes",
        "1",
        "-f",
        "rawvideo",
        "pipe:1",
    ]
    res = subprocess.run(cmd, capture_output=True, check=True)
    return res.stdout[0]


def test_smoke_sync_probe(tmp_path: Path):
    job_dir = tmp_path / "smoke_job"
    job_dir.mkdir()
    audio_dir = job_dir / "audio"
    audio_dir.mkdir()
    shutil.copy2("fixtures/music/test_bed.wav", audio_dir / "narration.wav")

    with open("renderer/test-data/timeline_smoke.json") as f:
        data = json.load(f)
    data["audio"]["narration"]["src"] = "job/audio/narration.wav"
    with open(job_dir / "timeline.json", "w") as f:
        json.dump(data, f, indent=2)

    mp4_path = job_dir / "smoke.mp4"
    cmd = [
        "npx",
        "--prefix",
        "renderer",
        "tsx",
        "renderer/scripts/render.ts",
        "media",
        "--job",
        str(job_dir),
        "--out",
        str(mp4_path),
        "--scale",
        "1.0",
        "--sync-probe",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Render failed: {res.stderr}"

    render_public = job_dir / "render_public"
    assert render_public.exists(), "render_public directory must exist"
    assert not (render_public / "fixtures").exists(), "render_public/fixtures must not exist"

    artifacts_dir = Path("artifacts")
    if artifacts_dir.exists():
        shutil.copy2(mp4_path, artifacts_dir / "smoke.mp4")

    luma29 = get_pixel_luma(mp4_path, 29)
    luma31 = get_pixel_luma(mp4_path, 31)
    luma59 = get_pixel_luma(mp4_path, 59)
    luma61 = get_pixel_luma(mp4_path, 61)

    assert luma29 < 40, f"Frame 29 luma {luma29} expected < 40"
    assert luma31 > 215, f"Frame 31 luma {luma31} expected > 215"
    assert luma59 > 215, f"Frame 59 luma {luma59} expected > 215"
    assert luma61 < 40, f"Frame 61 luma {luma61} expected < 40"
