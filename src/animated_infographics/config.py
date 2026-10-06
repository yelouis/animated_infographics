"""Global configuration and design constants."""

from typing import Final

__all__ = ["Final", "FPS", "WIDTH", "HEIGHT"]

FPS: Final[int] = 30
WIDTH: Final[int] = 1080
HEIGHT: Final[int] = 1920

# Audio pauses (ms)
PAUSE_AFTER_TITLE_MS: Final[int] = 800
PAUSE_BETWEEN_SENTENCES_MS: Final[int] = 250
PAUSE_BETWEEN_PARAGRAPHS_MS: Final[int] = 600
TAIL_SILENCE_MS: Final[int] = 500

# Transcription
ASR_PARAGRAPH_GAP_MS: Final[int] = 1200

# Mix volumes and fades
MUSIC_VOLUME: Final[float] = 0.126
MUSIC_FADE_IN_FRAMES: Final[int] = 30
MUSIC_FADE_OUT_FRAMES: Final[int] = 60
SFX_VOLUME: Final[float] = 0.35
SFX_MIN_GAP_FRAMES: Final[int] = 24

# Frame timing
LEAD_MS: Final[int] = 200
END_HOLD_MS: Final[int] = 1500
ENTER_FRAMES: Final[int] = 12
EXIT_FRAMES: Final[int] = 8

# Beat constraints
BEAT_MIN_MS: Final[int] = 1500
BEAT_TARGET_MIN_MS: Final[int] = 2500
BEAT_TARGET_MAX_MS: Final[int] = 6000
BEAT_MAX_MS: Final[int] = 8000
QUOTED_SENTENCE_MAX_MS: Final[int] = 16000

# Caption paging
CAPTION_MAX_WORDS: Final[int] = 3
CAPTION_MAX_CHARS: Final[int] = 22
CAPTION_MAX_GAP_MS: Final[int] = 700
CAPTION_TAIL_MS: Final[int] = 300
