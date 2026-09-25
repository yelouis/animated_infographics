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


def test_smoke_sync_probe():
    mp4_path = Path("artifacts/smoke.mp4")
    assert mp4_path.exists(), "smoke.mp4 must exist"

    luma29 = get_pixel_luma(mp4_path, 29)
    luma31 = get_pixel_luma(mp4_path, 31)
    luma59 = get_pixel_luma(mp4_path, 59)
    luma61 = get_pixel_luma(mp4_path, 61)

    assert luma29 < 40, f"Frame 29 luma {luma29} expected < 40"
    assert luma31 > 215, f"Frame 31 luma {luma31} expected > 215"
    assert luma59 > 215, f"Frame 59 luma {luma59} expected > 215"
    assert luma61 < 40, f"Frame 61 luma {luma61} expected < 40"
