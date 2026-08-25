"""FFT-based harmonic analysis: estimate the fundamental frequency and its harmonics."""

import numpy as np
import matplotlib.pyplot as plt

from _shared import load_wav


def estimate_fundamental(freqs, spectrum, min_freq=20.0, max_freq=5000.0, num_harmonics=3):
    """Harmonic Product Spectrum: pick the frequency whose harmonic series
    (f, 2f, 3f, ...) has the strongest combined energy, rather than just the
    single loudest bin. Plain peak-picking mis-detects piano notes as an
    octave too high whenever the 2nd harmonic outweighs the fundamental,
    which is common -- HPS is robust to that because the true fundamental's
    bin is reinforced by every harmonic, while the octave-up bin only lines
    up with every other one. Kept to the first few harmonics on purpose:
    piano partials drift sharp of exact integer multiples higher up
    (string stiffness / inharmonicity), so including too many weakens
    rather than strengthens the product.
    """
    candidates = np.where((freqs >= min_freq) & (freqs <= max_freq))[0]
    if len(candidates) == 0:
        candidates = np.arange(1, len(freqs))

    hps = spectrum[candidates].astype(np.float64).copy()
    for k in range(2, num_harmonics + 1):
        harmonic_idx = candidates * k
        valid = harmonic_idx < len(spectrum)
        hps[valid] *= spectrum[harmonic_idx[valid]]

    return freqs[candidates[np.argmax(hps)]]


def find_harmonics(sample_rate, data, max_harmonics=10, min_freq=20.0):
    n = len(data)
    windowed = data * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=1 / sample_rate)

    fundamental = estimate_fundamental(freqs, spectrum, min_freq=min_freq)

    harmonics = []
    search_width_hz = max(fundamental * 0.05, freqs[1] - freqs[0])
    for k in range(1, max_harmonics + 1):
        target = fundamental * k
        if target > freqs[-1]:
            break
        lo = np.searchsorted(freqs, target - search_width_hz)
        hi = np.searchsorted(freqs, target + search_width_hz)
        if hi <= lo:
            continue
        peak_idx = lo + np.argmax(spectrum[lo:hi])
        harmonics.append((freqs[peak_idx], spectrum[peak_idx]))

    return freqs, spectrum, fundamental, harmonics


def main():
    sample_rate, data, path = load_wav()
    freqs, spectrum, fundamental, harmonics = find_harmonics(sample_rate, data)

    print(f"File: {path.name}")
    print(f"Estimated fundamental frequency: {fundamental:.1f} Hz")
    print("\nHarmonics (frequency, relative amplitude):")
    for i, (freq, amp) in enumerate(harmonics, start=1):
        print(f"  {i:2d}: {freq:8.1f} Hz   {amp:.4f}")

    plt.figure(figsize=(10, 5))
    plt.plot(freqs, spectrum, linewidth=0.8)
    for freq, _ in harmonics:
        plt.axvline(freq, color="red", linestyle="--", alpha=0.4)
    plt.xlim(0, fundamental * (len(harmonics) + 2))
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude")
    plt.title(f"Spectrum — {path.name}")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
