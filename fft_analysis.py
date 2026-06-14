"""
fft_analysis.py  -  Corrected FFT analysis for predictive maintenance

Key improvements:
  1. Hann windowing to eliminate spectral leakage
  2. Amplitude normalisation (2/N scaling) so values are comparable across sessions
  3. Peak-picking with minimum bin distance - no more duplicate adjacent-bin entries
  4. DC / sub-5Hz exclusion to prevent current sensor offset contaminating top-5
  5. Full-spectrum downsampling uses maximum-in-bucket instead of stride to preserve peaks
"""

import numpy as np
from scipy.signal import find_peaks
from typing import List, Tuple

SAMPLING_RATE = 700   # Hz - must match app.py
MIN_FREQ_HZ   = 5.0   # exclude DC bleed and sub-rotation noise
MIN_PEAK_DISTANCE_HZ = 2.5   # two peaks must be at least 2.5 Hz apart
                              # at 700 Hz / 1400 points, bin width = 0.5 Hz
                              # so distance = 5 bins


def calculate_fft_analysis(values: List[float]) -> Tuple[List[float], List[float]]:
    """
    Calculate FFT and return the top-5 *distinct* frequency peaks and their
    physical amplitudes.

    Returns:
        (top_frequencies, top_amplitudes)
        Both lists have exactly 5 entries; unused slots are padded with 0.0.

    Key corrections vs original app.py version:
        - Hann window applied before FFT to prevent spectral leakage
        - Amplitudes normalised by (2 / window.sum()) - comparable across sessions
        - scipy find_peaks used with min distance to avoid adjacent-bin duplicates
        - Frequencies below MIN_FREQ_HZ excluded (DC offset bleed)
    """
    if not values or len(values) < 4:
        return [0.0] * 5, [0.0] * 5

    z = np.array(values, dtype=float)
    n = len(z)

    # 1. Subtract mean (remove DC before windowing - cleaner than just excluding bin 0)
    z = z - z.mean()

    # 2. Apply Hann window
    window = np.hanning(n)
    z_windowed = z * window

    # 3. FFT + normalised single-sided amplitude
    fft_result  = np.fft.rfft(z_windowed)           # rfft: only positive freqs
    freqs       = np.fft.rfftfreq(n, d=1.0 / SAMPLING_RATE)
    # Normalise: factor 2 for single-sided, divide by window sum (not N)
    # This gives amplitude in the same units as your input signal
    amps = (2.0 / window.sum()) * np.abs(fft_result)

    # 4. Exclude DC bleed (below MIN_FREQ_HZ)
    valid_mask = freqs >= MIN_FREQ_HZ
    freqs_v = freqs[valid_mask]
    amps_v  = amps[valid_mask]

    if len(amps_v) == 0:
        return [0.0] * 5, [0.0] * 5

    # 5. Find peaks with minimum separation to avoid adjacent-bin duplicates
    min_distance_bins = max(1, int(MIN_PEAK_DISTANCE_HZ / (SAMPLING_RATE / n)))
    peak_indices, _ = find_peaks(amps_v, distance=min_distance_bins)

    if len(peak_indices) == 0:
        # No peaks found - fall back to global top-5 (edge case: flat spectrum)
        top_idx = np.argsort(amps_v)[-5:][::-1]
    else:
        # Sort found peaks by amplitude descending, take top 5
        peak_amps   = amps_v[peak_indices]
        sorted_order = np.argsort(peak_amps)[::-1]
        top_idx      = peak_indices[sorted_order[:5]]

    top_frequencies = [float(freqs_v[i]) for i in top_idx]
    top_amplitudes  = [float(amps_v[i])  for i in top_idx]

    # Pad to exactly 5 entries
    while len(top_frequencies) < 5:
        top_frequencies.append(0.0)
        top_amplitudes.append(0.0)

    return top_frequencies[:5], top_amplitudes[:5]


def calculate_fft_full_spectrum(values: List[float]) -> Tuple[List[float], List[float]]:
    """
    Calculate full FFT spectrum for the frontend line chart.

    Returns up to 500 (frequency, amplitude) pairs using the same normalisation
    as calculate_fft_analysis so the chart amplitudes match the stored top-5 values.

    Downsampling uses maximum-in-bucket aggregation instead of stride so no
    real peaks are dropped when the spectrum is compressed.
    """
    if not values or len(values) < 4:
        return [], []

    z = np.array(values, dtype=float)
    n = len(z)

    z = z - z.mean()
    window      = np.hanning(n)
    z_windowed  = z * window
    fft_result  = np.fft.rfft(z_windowed)
    freqs       = np.fft.rfftfreq(n, d=1.0 / SAMPLING_RATE)
    amps        = (2.0 / window.sum()) * np.abs(fft_result)

    # Exclude sub-5Hz
    valid_mask  = freqs >= MIN_FREQ_HZ
    freqs_v     = freqs[valid_mask]
    amps_v      = amps[valid_mask]

    if len(freqs_v) == 0:
        return [], []

    MAX_POINTS = 500

    if len(freqs_v) <= MAX_POINTS:
        # Already under limit - return as-is
        return [round(float(f), 4) for f in freqs_v], \
               [round(float(a), 6) for a in amps_v]

    # Downsample: split into MAX_POINTS buckets, keep max amplitude per bucket
    # This guarantees no real spectral peak is swallowed by the stride
    bucket_size = len(freqs_v) / MAX_POINTS
    out_freqs: List[float] = []
    out_amps:  List[float] = []

    for i in range(MAX_POINTS):
        lo = int(i * bucket_size)
        hi = int((i + 1) * bucket_size)
        hi = min(hi, len(amps_v))
        if lo >= hi:
            continue
        bucket_amps  = amps_v[lo:hi]
        peak_in_bucket = int(np.argmax(bucket_amps))
        out_freqs.append(round(float(freqs_v[lo + peak_in_bucket]), 4))
        out_amps.append(round(float(bucket_amps[peak_in_bucket]), 6))

    return out_freqs, out_amps
