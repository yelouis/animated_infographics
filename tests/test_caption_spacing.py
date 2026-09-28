"""Caption word spacing check per design_visual_direction.md §8 and agent_execution_guide.md C5.

Within the caption band (y 1220–1460, full 1080×1920 resolution; y 610–730 at half scale):
- A column is a glyph column if any pixel has relative luminance > 0.5.
- Between the first and last glyph column there must be >= 2 runs of >= 16 empty columns
  at full resolution (>= 8 empty columns at half scale).
"""

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from PIL import Image


def compute_caption_empty_runs(img: Image.Image | np.ndarray) -> tuple[list[int], int]:
    """Compute the empty (non-glyph) column run lengths within the caption band.

    Returns (run_lengths, min_run_threshold).
    """
    if isinstance(img, Image.Image):
        arr = np.array(img.convert("RGB"))
    else:
        arr = img

    height = arr.shape[0]
    if height >= 1460:
        y_start, y_end = 1220, 1460
        min_run_threshold = 16
    else:
        y_start, y_end = 610, 730
        min_run_threshold = 8

    band = arr[y_start:y_end, :, :3].astype(float)
    # Relative luminance: 0.2126*R + 0.7152*G + 0.0722*B in [0, 1]
    lum = (0.2126 * band[:, :, 0] + 0.7152 * band[:, :, 1] + 0.0722 * band[:, :, 2]) / 255.0

    col_is_glyph = np.any(lum > 0.5, axis=0)
    glyph_indices = np.where(col_is_glyph)[0]
    if len(glyph_indices) == 0:
        return [], min_run_threshold

    first_col = int(glyph_indices[0])
    last_col = int(glyph_indices[-1])

    # Mask of non-glyph columns between first and last glyph column
    gap_mask: Sequence[bool] = ~col_is_glyph[first_col : last_col + 1]

    runs: list[int] = []
    current_run = 0
    for is_gap in gap_mask:
        if is_gap:
            current_run += 1
        else:
            if current_run > 0:
                runs.append(current_run)
                current_run = 0
    if current_run > 0:
        runs.append(current_run)

    return runs, min_run_threshold


def test_caption_spacing_synthetic() -> None:
    """Verify compute_caption_empty_runs correctly measures empty column runs."""
    img = np.zeros((1920, 1080, 3), dtype=np.uint8)
    # Put 3 words: columns 100..150, 170..220, 240..300 in caption band y 1300..1350
    # Gaps: 151..169 (19 px), 221..239 (19 px)
    img[1300:1350, 100:151] = [248, 244, 233]
    img[1300:1350, 170:221] = [255, 209, 102]
    img[1300:1350, 240:301] = [248, 244, 233]

    runs, thresh = compute_caption_empty_runs(img)
    assert thresh == 16
    assert runs == [19, 19]
    qualifying = [r for r in runs if r >= thresh]
    assert len(qualifying) >= 2


def test_caption_spacing_long_active() -> None:
    """Verify captions__long_active gallery fixture has >= 2 runs of >= 16 empty columns."""
    repo_root = Path(__file__).resolve().parents[1]
    candidate_paths = [
        repo_root / "artifacts" / "gallery" / "current" / "captions__long_active.png",
        repo_root / "renderer" / "goldens" / "captions__long_active.png",
    ]
    img_path = None
    for p in candidate_paths:
        if p.is_file():
            img_path = p
            break

    assert img_path is not None, (
        f"captions__long_active.png not found in {[str(p) for p in candidate_paths]}"
    )

    with Image.open(img_path) as im:
        runs, thresh = compute_caption_empty_runs(im)

    qualifying = [r for r in runs if r >= thresh]
    widest = max(runs) if runs else 0
    assert len(qualifying) >= 2, (
        f"{img_path.name}: expected >= 2 runs of >= {thresh} empty columns, "
        f"got {len(qualifying)} qualifying runs. All runs: {runs}, widest: {widest}px"
    )
