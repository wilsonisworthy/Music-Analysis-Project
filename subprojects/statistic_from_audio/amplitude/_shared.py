# router:skip
"""Shared WAV-picking/loading helper for the statistic_from_audio scripts."""

import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile


def _find_project_root(start):
    for parent in (start, *start.parents):
        if (parent / "main.py").exists() and (parent / "subprojects").exists():
            return parent
    raise RuntimeError("Could not find the project root (expected main.py + subprojects/ nearby)")


_PROJECT_ROOT = _find_project_root(Path(__file__).resolve())
_AUDIO_DIR = _PROJECT_ROOT / "Audio Recordings"

sys.path.insert(0, str(_PROJECT_ROOT))
from main import choose  # reuse the router's arrow-key / numbered-input menu


def select_wav():
    wav_files = sorted(_AUDIO_DIR.glob("*.wav"), key=lambda p: p.name.lower())
    if not wav_files:
        print(f"No .wav files found in '{_AUDIO_DIR.name}/'.")
        print(f"Add some recordings to {_AUDIO_DIR} and try again.")
        sys.exit(1)

    result = choose("Audio Recordings", [p.name for p in wav_files])
    if not isinstance(result, int):
        sys.exit(0)
    return wav_files[result]


def load_wav():
    """Let the user pick a WAV file from Audio Recordings/ and load it as
    float64 mono samples in [-1, 1]."""
    path = select_wav()
    sample_rate, data = wavfile.read(path)

    if data.ndim > 1:
        data = data.mean(axis=1)

    if np.issubdtype(data.dtype, np.integer):
        data = data.astype(np.float64) / np.iinfo(data.dtype).max
    else:
        data = data.astype(np.float64)

    return sample_rate, data, path
