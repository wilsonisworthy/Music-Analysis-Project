"""Batch export: pick a folder under Recordings/, run every WAV file found
under it (recursively) through the same attack/decay + brightness analysis
as amplitude/harmonics/compare, and dump the raw numbers to a CSV for
analysis later (e.g. correlating strike force with note properties across
a folder like Sample Recordings/{pp,mf,ff}/)."""

import csv
import re
from datetime import datetime

import numpy as np
from scipy.signal import stft

from _shared import _PROJECT_ROOT, _read_as_mono_float, select_folder

NOTE_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}
NOTE_PATTERN = re.compile(r"([A-Ga-g][b#]?)(-?\d+)$")

RESULTS_DIR = _PROJECT_ROOT / "Results"


def parse_pitch(stem):
    """Pull a trailing note+octave (e.g. 'C4', 'Db5') off a filename stem.
    Returns (note_name, octave) or (None, None) if nothing recognizable."""
    match = NOTE_PATTERN.search(stem)
    if not match:
        return None, None
    raw_name, octave = match.group(1), int(match.group(2))
    name = raw_name[0].upper() + raw_name[1:]
    if name not in NOTE_SEMITONE:
        return None, None
    return name, octave


# ---- amplitude analysis (same math as amplitude/main.py) ----

def compute_envelope(data, sample_rate, frame_ms=10):
    frame_size = max(1, int(sample_rate * frame_ms / 1000))
    n_frames = len(data) // frame_size
    trimmed = data[: n_frames * frame_size].reshape(n_frames, frame_size)
    rms = np.sqrt(np.mean(trimmed**2, axis=1))
    times = np.arange(n_frames) * frame_size / sample_rate
    return times, rms


def estimate_envelope(times, rms, silence_ratio=0.05):
    peak_idx = int(np.argmax(rms))
    peak_level = rms[peak_idx]
    if peak_level <= 0:
        return None
    attack_time = times[peak_idx]
    threshold = peak_level * silence_ratio
    tail = rms[peak_idx:]
    above = np.where(tail > threshold)[0]
    end_idx = peak_idx + int(above[-1]) if len(above) else peak_idx
    return {
        "attack_time_s": attack_time,
        "decay_time_s": max(times[end_idx] - attack_time, 0.0),
    }


# ---- harmonics/timbre analysis (same math as harmonics/main.py) ----

def analyze_spectrum(sample_rate, data, nperseg=4096, overlap=0.75, min_snr_db=15.0, noise_frames=5):
    """See single_note/harmonics/main.py's analyze_spectrum for the full
    explanation of the noise-floor SNR gate and spectral-subtraction fix."""
    noverlap = int(nperseg * overlap)
    freqs, times, Zxx = stft(data, fs=sample_rate, window="hann", nperseg=nperseg, noverlap=noverlap)
    magnitude = np.abs(Zxx)
    frame_energy = magnitude.sum(axis=0)
    noise_floor = max(np.median(frame_energy[:noise_frames]), 1e-15)
    snr_db = 10 * np.log10(np.maximum(frame_energy, 1e-15) / noise_floor)
    audible = snr_db > min_snr_db

    noise_profile = np.median(magnitude[:, :noise_frames], axis=1)
    denoised = np.maximum(magnitude - noise_profile[:, None], 0.0)

    safe_energy = np.maximum(denoised.sum(axis=0), 1e-15)
    centroid = (freqs[:, None] * denoised).sum(axis=0) / safe_energy

    return times, centroid, audible


def fit_brightness_trend(times, centroid):
    valid = ~np.isnan(centroid)
    if valid.sum() < 3:
        return None, None, None
    t, c = times[valid], centroid[valid]
    slope, intercept = np.polyfit(t, c, 1)
    start, end = intercept + slope * t[0], intercept + slope * t[-1]
    mean_level = c.mean()
    change_pct = (end - start) / mean_level * 100 if mean_level else 0.0
    return start, end, change_pct


def analyze_file(path):
    sample_rate, data = _read_as_mono_float(path)
    note, octave = parse_pitch(path.stem)

    times, rms = compute_envelope(data, sample_rate)
    env = estimate_envelope(times, rms)

    stft_times, centroid, audible = analyze_spectrum(sample_rate, data)
    trusted_centroid = np.where(audible, centroid, np.nan)
    bright_start, bright_end, bright_change_pct = fit_brightness_trend(stft_times, trusted_centroid)

    return {
        "file": str(path.relative_to(_PROJECT_ROOT)).replace("\\", "/"),
        "group": path.parent.name,
        "note": note or "",
        "octave": octave if octave is not None else "",
        "sample_rate_hz": sample_rate,
        "duration_s": round(len(data) / sample_rate, 4),
        "attack_time_s": round(env["attack_time_s"], 4) if env else "",
        "decay_time_s": round(env["decay_time_s"], 4) if env else "",
        "brightness_start_hz": round(bright_start, 1) if bright_start is not None else "",
        "brightness_end_hz": round(bright_end, 1) if bright_end is not None else "",
        "brightness_change_pct": round(bright_change_pct, 1) if bright_change_pct is not None else "",
        "brightness_frames_trusted": int(audible.sum()),
        "brightness_frames_total": len(audible),
    }


def main():
    folder = select_folder()
    wav_paths = sorted(folder.rglob("*.wav"))
    if not wav_paths:
        print(f"No .wav files found under {folder.relative_to(_PROJECT_ROOT)} (searched recursively).")
        return

    print(f"Analyzing {len(wav_paths)} file(s) under {folder.relative_to(_PROJECT_ROOT)}...")
    rows = []
    failed = []
    for i, path in enumerate(wav_paths, start=1):
        print(f"  [{i}/{len(wav_paths)}] {path.relative_to(_PROJECT_ROOT)}")
        try:
            rows.append(analyze_file(path))
        except Exception as e:
            failed.append((path, str(e)))

    RESULTS_DIR.mkdir(exist_ok=True)
    safe_name = folder.name.replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"{safe_name}_{timestamp}.csv"

    fieldnames = [
        "file", "group", "note", "octave", "sample_rate_hz", "duration_s",
        "attack_time_s", "decay_time_s",
        "brightness_start_hz", "brightness_end_hz", "brightness_change_pct",
        "brightness_frames_trusted", "brightness_frames_total",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} row(s) to {out_path.relative_to(_PROJECT_ROOT)}")
    if failed:
        print(f"{len(failed)} file(s) failed:")
        for path, err in failed:
            print(f"  {path.relative_to(_PROJECT_ROOT)}: {err}")


if __name__ == "__main__":
    main()
