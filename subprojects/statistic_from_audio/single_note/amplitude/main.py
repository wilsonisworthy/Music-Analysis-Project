"""Amplitude envelope analysis: attack and decay."""

import numpy as np
import matplotlib.pyplot as plt

from _shared import load_wav


def compute_envelope(data, sample_rate, frame_ms=10):
    frame_size = max(1, int(sample_rate * frame_ms / 1000))
    n_frames = len(data) // frame_size
    trimmed = data[: n_frames * frame_size].reshape(n_frames, frame_size)
    rms = np.sqrt(np.mean(trimmed**2, axis=1))
    times = np.arange(n_frames) * frame_size / sample_rate
    return times, rms


def estimate_envelope(times, rms, silence_ratio=0.05):
    """Attack/decay estimate from an RMS envelope: attack is silence -> peak,
    decay is peak -> the point the level drops back below a near-silence
    threshold. No sustain phase -- struck/decaying instruments like piano
    don't hold a plateau, they just decay continuously after the attack.
    """
    peak_idx = int(np.argmax(rms))
    peak_level = rms[peak_idx]
    if peak_level <= 0:
        return None

    attack_time = times[peak_idx]
    silence_threshold = peak_level * silence_ratio
    tail = rms[peak_idx:]

    above = np.where(tail > silence_threshold)[0]
    end_idx = peak_idx + int(above[-1]) if len(above) else peak_idx

    return {
        "attack_time_s": attack_time,
        "decay_time_s": max(times[end_idx] - attack_time, 0.0),
        "peak_level": float(peak_level),
        "end_idx": end_idx,
    }


def main():
    sample_rate, data, path = load_wav()
    times, rms = compute_envelope(data, sample_rate)
    envelope = estimate_envelope(times, rms)

    print(f"File: {path.name}")
    if envelope:
        print(f"Attack: {envelope['attack_time_s']:.3f} s (silence -> peak of {envelope['peak_level']:.4f})")
        print(f"Decay:  {envelope['decay_time_s']:.3f} s (peak -> near-silence)")
    else:
        print("Silent file, nothing to estimate.")

    plt.figure(figsize=(10, 4))
    plt.plot(times, rms, linewidth=0.8, label="RMS amplitude envelope")
    if envelope:
        plt.axvline(envelope["attack_time_s"], color="green", linestyle="--", label="Attack ends")
        plt.axvline(times[envelope["end_idx"]], color="red", linestyle="--", label="Decay ends")
    plt.xlabel("Time (s)")
    plt.ylabel("RMS amplitude")
    plt.title(f"Amplitude envelope — {path.name}")
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
