"""
fault_pump_cavitation.py
========================
Fault simulation: PUMP CAVITATION

Physical description
--------------------
Cavitation occurs when local fluid pressure drops below the vapour pressure,
forming vapour bubbles that then collapse violently as they move into higher-
pressure regions of the impeller.

Each bubble collapse is a microscopic implosion — a pressure shock with a
rise time of microseconds and energy concentrated in the 1–50 kHz range.
At 700 Hz sample rate we observe the low-frequency envelope of these events:
broadband random impulses with no dominant frequency — the statistical
fingerprint is impulsive kurtosis, not a spectral peak.

Progression stages:
  Incipient  → occasional isolated bubble events (mild kurtosis rise)
  Developed  → continuous bubble cloud — sustained broadband noise
  Supercavitation → large vapour cavity forms, pump efficiency collapses,
                    current drops as hydraulic load falls

Sensor signatures
-----------------
Audio [LEAD, lag=0]
  • "Gravel in the pump" — crackling, hissing, broadband 200–350 Hz envelope
  • Kurtosis ↑↑↑ (most sensitive early indicator)
  • Broadband amplitude rises without tonal peaks
  • At supercavitation: sustained hiss, kurtosis drops slightly (continuous)

Acceleration [lag=2]
  • Random broadband impulses — no dominant frequency
  • Kurtosis ↑↑ (impulsive character)
  • Skewness ↑ (collapse events are one-sided pressure shocks)
  • RMS grows with developed cavitation
  • At supercavitation: high sustained broadband

Current [lag=4]
  • Load fluctuation as pump efficiency degrades → current variance rises
  • Counter-intuitive: mean current eventually FALLS as hydraulic load collapses
    (less work being done — pump is moving vapour not liquid)
  • Range ↑ throughout (efficiency oscillation)
  • This current drop is a key ML differentiator
"""

import os
import math
import random
from datetime import datetime

from base_motor import (
    MOTOR, SAMPLE_RATE, N_SAMPLES, TOTAL_UPLOADS,
    sensor_deviation, make_timestamps, gaussian_noise,
    sinusoid, add_impulses,
    save_max_min_csvs, run_fault_simulation,
)

FAULT_NAME = 'pump_cavitation'

# Cavitation characteristic frequency bands (within 700 Hz capture range)
F_CAVITATION_LOW  = 120.0   # Hz — low end of bubble collapse envelope
F_CAVITATION_MID  = 220.0   # Hz — mid band
F_CAVITATION_HIGH = 310.0   # Hz — high band (approaches Nyquist at 350 Hz)


# ─────────────────────────────────────────────
# AUDIO GENERATOR
# ─────────────────────────────────────────────
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio leads with lag=0.

    Key signatures:
      Incipient (dev 0–0.30):
        • Occasional crackle bursts — high kurtosis, low mean dB
        • Broadband noise floor rises slightly

      Developed (dev 0.30–0.75):
        • Continuous hiss + crackle — sustained broadband 120–310 Hz content
        • Mean dB rises, kurtosis remains high

      Supercavitation (dev > 0.75):
        • Loud continuous hiss — kurtosis drops (more continuous, less impulsive)
        • Mean dB peaks (~100 dB) — large vapour cavity radiating noise
    """
    dev = sensor_deviation(upload_num, onset, lag=0, steepness=0.43)
    ts  = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB

    # Healthy baseline
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]

    if dev < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    # ── Stage classification ──
    incipient     = min(dev / 0.30, 1.0)
    developed     = max(min((dev - 0.30) / 0.45, 1.0), 0.0)
    supercavit    = max((dev - 0.75) / 0.25, 0.0)

    # ── SPL rise ──
    # Incipient: +3 dB, Developed: +12 dB, Supercavitation: +18 dB
    db_level = (base_db
                + incipient  * 3.0
                + developed  * 9.0
                + supercavit * 6.0)

    # ── Broadband cavitation frequency bands ──
    cav_low  = base_db * 0.010 * dev
    cav_mid  = base_db * 0.016 * (incipient * 0.3 + developed * 0.7 + supercavit)
    cav_high = base_db * 0.012 * (developed * 0.5 + supercavit)

    sig_cav_low  = sinusoid(F_CAVITATION_LOW,  cav_low,
                            phase=random.uniform(0, 2*math.pi))
    sig_cav_mid  = sinusoid(F_CAVITATION_MID,  cav_mid,
                            phase=random.uniform(0, 2*math.pi))
    sig_cav_high = sinusoid(F_CAVITATION_HIGH, cav_high,
                            phase=random.uniform(0, 2*math.pi))

    # ── Broadband noise floor (dominant character) ──
    broadband_sigma = 1.2 + dev * 6.5
    noise_broadband = gaussian_noise(broadband_sigma)

    signal = [db_level * 0.04 + v + cl + cm + ch
              for v, cl, cm, ch
              in zip(noise_broadband,
                     sig_cav_low, sig_cav_mid, sig_cav_high)]

    # ── Crackle impulses (bubble collapse events) ──
    # Incipient: sparse, high-magnitude; Developed: dense; Supercav: very dense
    if dev > 0.05:
        crackle_rate = 3.0 + incipient * 8.0 + developed * 20.0 + supercavit * 15.0
        crackle_mag  = db_level * (0.20 * incipient + 0.14 * developed
                                   + 0.08 * supercavit)
        signal = add_impulses(signal, rate=crackle_rate,
                              magnitude=crackle_mag, decay=0.45)

    signal = [min(s, 108.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL≈{db_level:.1f}dB  '
                f'stage: inc={incipient:.2f} dev={developed:.2f} sup={supercavit:.2f}')


# ─────────────────────────────────────────────
# ACCELERATION GENERATOR
# ─────────────────────────────────────────────
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration lags audio by 2 uploads.

    Key signatures:
      • Random broadband impulses — NO dominant frequency (key differentiator
        from bearing fault which has BPFO/BPFI peaks)
      • Kurtosis ↑↑ — most sensitive statistical indicator
      • Skewness ↑ (collapse shock waves are compressive — one-sided)
      • RMS growth is moderate compared to kurtosis growth
    """
    dev = sensor_deviation(upload_num, onset, lag=2, steepness=0.43)
    ts  = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g
    f_rot  = MOTOR['f_rot']          # 12.25 Hz — always present
    f_bpf  = MOTOR['bpf']            # 73.5 Hz — blade pass (mild at healthy)

    # Healthy baseline
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_g * 0.28))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    incipient  = min(dev / 0.30, 1.0)
    developed  = max(min((dev - 0.30) / 0.45, 1.0), 0.0)
    supercavit = max((dev - 0.75) / 0.25, 0.0)

    # ── Broadband noise floor growth ──
    # Kurtosis is the key stat — broadband + impulses drives it up
    broadband_rms = base_g * (0.10 + dev * 1.20)
    noise_broad   = gaussian_noise(broadband_rms)

    # Rotational component persists (motor still spinning)
    sig_rot = sinusoid(f_rot, base_g * 0.28)

    # BPF mildly present (impeller still rotating, just cavitating)
    bpf_amp = base_g * 0.06 * (1.0 - supercavit * 0.5)
    sig_bpf = sinusoid(f_bpf, bpf_amp)

    signal = [base_g * 0.04 + v + r + b
              for v, r, b
              in zip(noise_broad, sig_rot, sig_bpf)]

    # ── Impulsive cavitation collapse shocks ──
    # Dense random broadband — no periodicity (key vs bearing fault)
    if dev > 0.05:
        collapse_rate = (5.0 * incipient
                         + 25.0 * developed
                         + 40.0 * supercavit)
        # Magnitude: sharp but moderate — collapses transmit through fluid
        collapse_mag  = base_g * (0.35 * incipient
                                  + 0.55 * developed
                                  + 0.45 * supercavit)
        signal = add_impulses(signal, rate=collapse_rate,
                              magnitude=collapse_mag, decay=0.50)

    # ── Amplitude modulation (vapour cloud oscillation at developed stage) ──
    if developed > 0.30:
        mod_depth = developed * 0.28
        mod_freq  = 4.5   # Hz
        n = len(signal)
        signal = [signal[i] * (1.0 + mod_depth *
                                math.sin(2 * math.pi * mod_freq * i / SAMPLE_RATE))
                  for i in range(n)]

    rms_est = (sum(s**2 for s in signal) / len(signal)) ** 0.5
    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev={dev:.3f}  RMS≈{rms_est:.3f}g  '
                f'collapse_rate≈{5.0*incipient+25.0*developed+40.0*supercavit:.1f}/s')


# ─────────────────────────────────────────────
# CURRENT GENERATOR
# ─────────────────────────────────────────────
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current lags audio by 4 uploads.

    Counter-intuitive signature (key ML differentiator):
      • Phase 1 (dev 0–0.40): current FLUCTUATES — pump efficiency oscillating
        Range ↑, Mean near rated
      • Phase 2 (dev 0.40–0.75): current starts dropping — hydraulic load
        collapses as vapour cavity grows (pump moves vapour not liquid)
      • Phase 3 (dev > 0.75): current settles LOW (~15–25% below rated)
        Pump is effectively running unloaded on vapour

    This downward current trend combined with high audio kurtosis is the
    definitive cavitation fingerprint for the ML model.
    """
    dev = sensor_deviation(upload_num, onset, lag=4, steepness=0.43)
    ts  = make_timestamps(datetime.now())

    rated  = MOTOR['rated_current_a']    # 375 A
    f_sup  = MOTOR['f_supply']           # 50 Hz
    f_rot  = MOTOR['f_rot']             # 12.25 Hz
    f_bpf  = MOTOR['bpf']              # 73.5 Hz

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    fluctuate  = min(dev / 0.40, 1.0)
    load_drop  = max((dev - 0.40) / 0.35, 0.0)
    unloaded   = max((dev - 0.75) / 0.25, 0.0)

    # ── DC level: rises slightly then drops below rated ──
    dc_level = (rated
                + fluctuate * rated * 0.04      # slight rise in fluctuation phase
                - load_drop * rated * 0.12      # drops as load collapses
                - unloaded  * rated * 0.10)     # further drop at supercavitation
    dc_level = max(dc_level, rated * 0.65)      # floor: motor still runs

    # ── Variance increase (efficiency oscillation) ──
    variance_scale = 1.0 + fluctuate * 5.5
    noise_sigma_fault = rated * 0.004 * variance_scale

    # ── BPF current modulation (impeller efficiency pulsing) ──
    bpf_amp = rated * 0.025 * fluctuate * (1.0 - unloaded * 0.6)
    sig_bpf = sinusoid(f_bpf, bpf_amp)
    sig_sup = sinusoid(f_sup, rated * 0.08)

    signal = [dc_level + v + ss + sb
              for v, ss, sb
              in zip(gaussian_noise(noise_sigma_fault), sig_sup, sig_bpf)]

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_level:.1f}A  '
                f'(rated={rated:.0f}A)  variance_scale={variance_scale:.2f}  '
                f'drop={load_drop:.2f}  unloaded={unloaded:.2f}')


# ─────────────────────────────────────────────
# COMBINED GENERATE FUNCTION
# ─────────────────────────────────────────────
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> None:
    generate_audio(upload_num, onset, data_dir, logger)
    generate_acceleration(upload_num, onset, data_dir, logger)
    generate_current(upload_num, onset, data_dir, logger)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    run_fault_simulation(
        fault_name    = FAULT_NAME,
        generate_fn   = generate_all,
        sleep_seconds = 30,
    )
