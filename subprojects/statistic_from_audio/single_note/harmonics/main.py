"""Timbre-over-time analysis: how the spectrum (and brightness) evolves
during a note, via a spectrogram (FFT over time) and spectral centroid."""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft

from _shared import load_wav


def analyze_spectrum(sample_rate, data, nperseg=4096, overlap=0.75, min_snr_db=15.0, noise_frames=5):
    """Run an STFT and derive a per-frame brightness (spectral centroid) --
    the amplitude-weighted average frequency. Higher = more energy in the
    upper harmonics (brighter/thinner), lower = energy concentrated near
    the fundamental (darker/warmer).

    Frames are flagged "audible" once they're min_snr_db above the noise
    floor (estimated from the first few frames, which are silence before
    the note's attack) -- used by the caller to style the trusted vs.
    untrusted portion of the brightness line differently.

    The centroid itself is computed with spectral subtraction: the noise's
    own shape is measured per frequency bin (not just one overall level)
    from those same pre-attack frames, then subtracted from every frame
    before weighting the centroid, clamping anything that goes negative to
    zero. Without this, a frame that's mostly noise still gets averaged
    using its raw magnitude -- and a flat noise floor spread across the
    entire FFT range (up to ~22kHz here) has a much higher inherent
    "center of mass" than the note's own harmonics, which live down in
    the hundreds-to-low-thousands of Hz. That mismatch was what dragged
    the brightness reading upward as a note faded, even though nothing
    about the note itself was getting brighter. Subtracting the noise's
    own per-bin shape cancels that out at the source, instead of just
    refusing to trust frames once it happens.
    """
    noverlap = int(nperseg * overlap)
    freqs, times, Zxx = stft(data, fs=sample_rate, window="hann", nperseg=nperseg, noverlap=noverlap)
    magnitude = np.abs(Zxx)

    frame_energy = magnitude.sum(axis=0)
    noise_floor = max(np.median(frame_energy[:noise_frames]), 1e-15)
    snr_db = 10 * np.log10(np.maximum(frame_energy, 1e-15) / noise_floor)
    audible = snr_db > min_snr_db

    noise_profile = np.median(magnitude[:, :noise_frames], axis=1)
    denoised = np.maximum(magnitude - noise_profile[:, None], 0.0)

    # Centroid computed for every frame, not just trusted ones, so the
    # caller can still plot the untrusted tail (just styled differently)
    # instead of the line simply vanishing once SNR drops too low.
    safe_energy = np.maximum(denoised.sum(axis=0), 1e-15)
    centroid = (freqs[:, None] * denoised).sum(axis=0) / safe_energy

    return freqs, times, magnitude, centroid, audible


def describe_brightness_trend(times, centroid):
    valid = ~np.isnan(centroid)
    if valid.sum() < 3:
        return "Not enough signal above the noise floor to judge a timbre trend."

    t, c = times[valid], centroid[valid]
    slope, intercept = np.polyfit(t, c, 1)
    start, end = intercept + slope * t[0], intercept + slope * t[-1]
    mean_level = c.mean()
    change_pct = (end - start) / mean_level * 100 if mean_level else 0.0

    if abs(change_pct) < 8:
        trend = "stays roughly constant -- timbre doesn't change much over the note"
    elif change_pct < 0:
        trend = "gets darker over time (upper harmonics fading faster than the fundamental)"
    else:
        trend = "gets brighter over time"

    return f"Brightness (fitted trend): {start:.0f} Hz -> {end:.0f} Hz ({change_pct:+.1f}%)\n{trend}"


def main():
    sample_rate, data, path = load_wav()
    freqs, times, magnitude, centroid, audible = analyze_spectrum(sample_rate, data)
    trusted_centroid = np.where(audible, centroid, np.nan)

    print(f"File: {path.name}")
    print(describe_brightness_trend(times, trusted_centroid))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    max_freq = min(freqs[-1], 8000)
    freq_mask = freqs <= max_freq
    magnitude_db = 20 * np.log10(magnitude[freq_mask] + 1e-9)
    magnitude_db -= magnitude_db.max()

    pcm = ax1.pcolormesh(times, freqs[freq_mask], magnitude_db, shading="auto", cmap="magma", vmin=-80, vmax=0)
    fig.colorbar(pcm, ax=ax1, label="Magnitude (dB, relative to peak)")
    ax1.plot(times, np.clip(centroid, 0, max_freq), color="gray", linestyle="--", linewidth=1, alpha=0.7,
              label="Brightness (below noise floor)")
    ax1.plot(times, np.clip(trusted_centroid, 0, max_freq), color="cyan", linewidth=1.4,
              label="Brightness (above noise floor)")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.set_ylabel("Frequency (Hz)")
    ax1.set_title(f"Spectrogram — {path.name}")

    ax2.plot(times, centroid, color="gray", linestyle="--", linewidth=1, alpha=0.7, label="Below noise floor")
    ax2.plot(times, trusted_centroid, color="cyan", linewidth=1.5, label="Above noise floor")
    ax2.legend(fontsize=8)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Spectral centroid (Hz)")
    ax2.set_title("Brightness over time")
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
