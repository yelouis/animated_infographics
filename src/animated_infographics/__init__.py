"""Animated Infographics generator."""

import os
from pathlib import Path

# Ensure HF_HOME points to where models are cached if current HF_HOME lacks them
_default_hf = Path.home() / ".cache" / "huggingface"
if _default_hf.joinpath("hub", "models--hexgrad--Kokoro-82M").exists():
    _hf_home = os.environ.get("HF_HOME")
    if not _hf_home or not Path(_hf_home).joinpath("hub", "models--hexgrad--Kokoro-82M").exists():
        os.environ["HF_HOME"] = str(_default_hf)

__version__ = "0.1.0"
