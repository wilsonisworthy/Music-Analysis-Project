"""Cross-analysis across multiple recordings: pick several files, pick
which analysis to run, and see each recording's own plot(s) side by side
(same look as running amplitude/harmonics individually), with a plain
numbers table underneath -- not another graph."""

import re

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft

from _shared import choose, load_wavs

NOTE_SEMITONE = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5,
    "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}
NOTE_PATTERN = re.compile(r"([A-Ga-g][b#]?)(-?\d+)$")


def parse_pitch(stem):
    """Pull a trailing note+octave (e.g. 'C4', 'Db5') off a filename stem
    and turn it into a MIDI-ish number for sorting by pitch.
    Returns (sort_key, label) or (None, stem) if nothing recognizable."""
    match = NOTE_PATTERN.search(stem)
    if not match:
        return None, stem
    raw_name, octave = match.group(1), int(match.group(2))
    name = raw_name[0].upper() + raw_name[1:]
    if name not in NOTE_SEMITONE:
        return None, stem
    return NOTE_SEMITONE[name] + (octave + 1) * 12, f"{name}{octave}"


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
        "end_idx": end_idx,
    }


def plot_amplitude(ax, sample_rate, data, label):
    times, rms = compute_envelope(data, sample_rate)
    env = estimate_envelope(times, rms)
    ax.plot(times, rms, linewidth=0.8, color="steelblue")
    if env:
        ax.axvline(env["attack_time_s"], color="green", linestyle="--", linewidth=1, label="Attack")
        ax.axvline(times[env["end_idx"]], color="red", linestyle="--", linewidth=1, label="Decay end")
        ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"{label} — amplitude", fontsize=9)
    ax.set_xlabel("Time (s)", fontsize=8)
    ax.set_ylabel("RMS amplitude", fontsize=8)
    ax.tick_params(labelsize=7)
    return env


# ---- harmonics/timbre analysis (same math as harmonics/main.py) ----

def analyze_spectrum(sample_rate, data, nperseg=4096, overlap=0.75, min_snr_db=15.0, noise_frames=5):
    """See harmonics/main.py's analyze_spectrum for the full explanation --
    centroid uses spectral subtraction (per-bin noise profile from the
    pre-attack frames, subtracted before weighting) so a mostly-noise
    frame doesn't drag the reading toward the noise floor's own much
    wider, higher-frequency-weighted "center of mass"."""
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

    return freqs, times, magnitude, centroid, audible


def fit_brightness_trend(times, centroid):
    valid = ~np.isnan(centroid)
    if valid.sum() < 3:
        return None
    t, c = times[valid], centroid[valid]
    slope, intercept = np.polyfit(t, c, 1)
    return intercept + slope * t[0], intercept + slope * t[-1]


def plot_harmonics(ax, sample_rate, data, label):
    freqs, times, magnitude, centroid, audible = analyze_spectrum(sample_rate, data)
    trusted_centroid = np.where(audible, centroid, np.nan)

    max_freq = min(freqs[-1], 8000)
    freq_mask = freqs <= max_freq
    magnitude_db = 20 * np.log10(magnitude[freq_mask] + 1e-9)
    magnitude_db -= magnitude_db.max()

    ax.pcolormesh(times, freqs[freq_mask], magnitude_db, shading="auto", cmap="magma", vmin=-80, vmax=0)
    ax.plot(times, np.clip(centroid, 0, max_freq), color="gray", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.plot(times, np.clip(trusted_centroid, 0, max_freq), color="cyan", linewidth=1.2)
    ax.set_title(f"{label} — harmonics", fontsize=9)
    ax.set_xlabel("Time (s)", fontsize=8)
    ax.set_ylabel("Frequency (Hz)", fontsize=8)
    ax.tick_params(labelsize=7)
    return fit_brightness_trend(times, trusted_centroid)


def main():
    recordings = load_wavs()

    mode_options = ["Amplitude", "Harmonics", "Both"]
    mode = choose("What do you want to analyze?", mode_options)
    if not isinstance(mode, int):
        return
    show_amp = mode_options[mode] in ("Amplitude", "Both")
    show_harm = mode_options[mode] in ("Harmonics", "Both")
    n_cols = int(show_amp) + int(show_harm)

    entries = []
    for sample_rate, data, path in recordings:
        sort_key, label = parse_pitch(path.stem)
        entries.append((sort_key if sort_key is not None else 0, label, sample_rate, data))
    entries.sort(key=lambda e: (e[0], e[1]))

    n_rows = len(entries)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6.5 * n_cols, 3 * n_rows), squeeze=False)

    table_rows = []
    for i, (_, label, sample_rate, data) in enumerate(entries):
        col = 0
        env = None
        trend = None
        if show_amp:
            env = plot_amplitude(axes[i][col], sample_rate, data, label)
            col += 1
        if show_harm:
            trend = plot_harmonics(axes[i][col], sample_rate, data, label)
            col += 1
        table_rows.append((label, env, trend))

    plt.tight_layout()

    header = f"{'note':10s} {'attack (s)':>10s} {'decay (s)':>10s} {'bright start':>13s} {'bright end':>11s}"
    print(header)
    print("-" * len(header))
    for label, env, trend in table_rows:
        attack_s = f"{env['attack_time_s']:.3f}" if env else "n/a"
        decay_s = f"{env['decay_time_s']:.3f}" if env else "n/a"
        bs = f"{trend[0]:.0f} Hz" if trend else "n/a"
        be = f"{trend[1]:.0f} Hz" if trend else "n/a"
        print(f"{label:10s} {attack_s:>10s} {decay_s:>10s} {bs:>13s} {be:>11s}")

    plt.show()


if __name__ == "__main__":
    main()
