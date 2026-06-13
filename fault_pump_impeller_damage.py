"""
fault_pump_impeller_damage.py
==============================
Fault simulation: PUMP IMPELLER DAMAGE

Physical description
--------------------
One or more impeller blades are chipped, broken, or eroded.
A 6-blade impeller at 735 RPM produces a Blade Pass Frequency of:
  BPF = (735 / 60) × 6 = 73.5 Hz

With a damaged blade, one pass per revolution produces a stronger impulse
than the others — this creates a periodic impact at the rotational frequency
(12.25 Hz) superimposed on the BPF signature.

As damage grows:
  • BPF amplitude increases and becomes irregular
  • 1× rotational (12.25 Hz) grows as hydraulic asymmetry worsens
  • 2× BPF harmonics appear (147 Hz) as damage becomes severe
  • Pump efficiency drops → current modulation at BPF and 1×

Distinguishable from:
  • Bearing fault:  bearing fault frequencies (BPFO=52 Hz, BPFI=73 Hz) vs
                    BPF=73.5 Hz. The BPF is periodic with impeller rotation;
                    bearing defect frequencies are not locked to blade count.
                    Also: acceleration kurtosis in bearing fault is higher
                    because impacts are more impulsive.
  • Cavitation:     cavitation is broadband/random, impeller damage is periodic.
  • Misalignment:   misalignment has strong 2× rotational (24.5 Hz), not BPF.

Sensor signatures
-----------------
Acceleration [LEAD, lag=0] — simultaneously with Audio
  • Periodic impact at BPF (73.5 Hz) — amplitude grows with damage
  • 1× rotational (12.25 Hz) grows as hydraulic imbalance worsens
  • 2× BPF (147 Hz) appears at severe stage
  • Kurtosis ↑ (periodic impacts are impulsive at onset, then more sustained)
  • Top frequencies: 73.5 Hz, 12.25 Hz, 147 Hz in order of appearance

Audio [LEAD, lag=0] — simultaneously with Acceleration
  • Thumping at BPF (73.5 Hz) — distinct from cavitation hiss
  • At severe stage: fluid-borne noise grows, broadband floor rises
  • SPL rises moderately (82 → ~94 dB)
  • Top frequency = BPF = 73.5 Hz (key identifier)

Current [lag=4]
  • BPF modulation on current — hydraulic load pulsing at blade pass rate
  • 1× rotational modulation grows with hydraulic imbalance
  • Mean current drops slightly (damaged impeller moves less fluid → less work)
  • Range ↑ as load pulsation grows
"""

import os
import math
import random
from datetime import datetime

from base_motor import (
    MOTOR, SAMPLE_RATE, N_SAMPLES, TOTAL_UPLOADS,
    sensor_deviation, make_timestamps, gaussian_noise,
    sinusoid, add_impulses, amplitude_modulate,
    save_max_min_csvs, run_fault_simulation,
)

FAULT_NAME = 'pump_impeller_damage'

F_BPF  = MOTOR['bpf']       # 73.5 Hz — blade pass frequency
F_ROT  = MOTOR['f_rot']     # 12.25 Hz — 1× rotational
F_2ROT = MOTOR['f_2x']      # 24.50 Hz — 2× rotational
F_2BPF = F_BPF * 2          # 147.0 Hz — 2× BPF harmonic


# ─────────────────────────────────────────────
# ACCELERATION GENERATOR
# ─────────────────────────────────────────────
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration leads with lag=0.

    Frequency evolution:
      dev 0.00–0.20 : BPF appears at low amplitude (slight kurtosis rise)
      dev 0.20–0.55 : BPF grows + 1× rotational rises (hydraulic imbalance)
      dev 0.55–0.80 : 2× BPF harmonic appears
      dev > 0.80    : Broadband floor rises (fragmented blade causes chaotic flow)
    """
    dev = sensor_deviation(upload_num, onset, lag=0, steepness=0.43)
    ts  = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g

    # Healthy baseline
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(F_ROT, base_g * 0.28))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    # ── Stage modifiers ──
    early    = min(dev / 0.20, 1.0)
    mid      = max(min((dev - 0.20) / 0.35, 1.0), 0.0)
    harmonic = max(min((dev - 0.55) / 0.25, 1.0), 0.0)
    severe   = max((dev - 0.80) / 0.20, 0.0)

    # ── BPF component — primary fault signature ──
    bpf_amp = base_g * (early * 0.35 + mid * 1.10 + harmonic * 0.55
                        + severe * 0.30)
    sig_bpf = sinusoid(F_BPF, bpf_amp,
                       phase=random.uniform(0, 2 * math.pi))

    # ── 1× rotational — hydraulic imbalance from damaged blade ──
    rot_amp  = base_g * (0.28 + mid * 0.85 + harmonic * 0.45)
    sig_rot  = sinusoid(F_ROT, rot_amp)

    # ── 2× BPF harmonic — appears at severe stage ──
    bpf2_amp = base_g * harmonic * 0.50
    sig_bpf2 = sinusoid(F_2BPF, bpf2_amp)

    # ── 2× rotational — secondary hydraulic asymmetry ──
    rot2_amp = base_g * mid * 0.20
    sig_rot2 = sinusoid(F_2ROT, rot2_amp)

    # ── Broadband floor rises at severe stage (blade fragmentation) ──
    broadband_sigma = base_g * (0.10 + dev * 0.35 + severe * 0.60)
    noise_fault = gaussian_noise(broadband_sigma)

    signal = [base_g * 0.04 + v + b + r + b2 + r2
              for v, b, r, b2, r2
              in zip(noise_fault, sig_bpf, sig_rot, sig_bpf2, sig_rot2)]

    # ── Periodic impacts at BPF — impulsive character ──
    # Each blade pass of the damaged blade creates an impact
    if dev > 0.08:
        impact_rate = F_BPF     # impacts at blade pass rate
        impact_mag  = base_g * dev * 0.90
        # Vary magnitude per impact (damage is not perfectly uniform)
        signal = add_impulses(signal, rate=impact_rate,
                              magnitude=impact_mag, decay=0.78)

    rms_est = (sum(s**2 for s in signal) / len(signal)) ** 0.5
    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev={dev:.3f}  BPF={bpf_amp:.3f}g  '
                f'ROT={rot_amp:.3f}g  2×BPF={bpf2_amp:.3f}g  RMS≈{rms_est:.3f}g')


# ─────────────────────────────────────────────
# AUDIO GENERATOR
# ─────────────────────────────────────────────
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio leads with lag=0 (simultaneous with acceleration).

    Key signatures:
      • Thumping/knocking at BPF (73.5 Hz) — rhythmic, not random
      • This is the defining audio difference from cavitation (which is hiss/crackle)
      • SPL rises moderately
      • At severe stage: fluid noise adds broadband content
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

    early    = min(dev / 0.20, 1.0)
    mid      = max(min((dev - 0.20) / 0.35, 1.0), 0.0)
    severe   = max((dev - 0.80) / 0.20, 0.0)

    # ── SPL rise (moderate) ──
    max_db_rise = 12.0
    db_level    = base_db + dev * max_db_rise

    # ── BPF thumping (dominant audio signature) ──
    thump_amp = (db_level - base_db) * (0.30 * early + 0.55 * mid + 0.15 * severe)
    sig_thump = sinusoid(F_BPF, thump_amp,
                         phase=random.uniform(0, 2 * math.pi))

    # ── 1× rotational in audio (hydraulic imbalance) ──
    rot_audio = (db_level - base_db) * 0.15 * mid
    sig_rot   = sinusoid(F_ROT, rot_audio)

    # ── 2× BPF harmonic in audio (severe stage) ──
    bpf2_audio = (db_level - base_db) * 0.10 * severe
    sig_bpf2   = sinusoid(F_2BPF, bpf2_audio)

    # ── Broadband noise (fluid turbulence from damaged blade) ──
    broadband_sigma = 1.2 + dev * 3.5
    noise_broadband = gaussian_noise(broadband_sigma)

    signal = [db_level * 0.04 + v + t + r + b2
              for v, t, r, b2
              in zip(noise_broadband, sig_thump, sig_rot, sig_bpf2)]

    # ── Rhythmic thumps at BPF (audible impacts) ──
    if dev > 0.10:
        thump_rate = F_BPF
        thump_mag  = (db_level - base_db) * 0.25 * dev
        signal = add_impulses(signal, rate=thump_rate,
                              magnitude=thump_mag, decay=0.65)

    signal = [min(s, 102.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL≈{db_level:.1f}dB  '
                f'BPF_amp={thump_amp:.1f}dB')


# ─────────────────────────────────────────────
# CURRENT GENERATOR
# ─────────────────────────────────────────────
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current lags acceleration by 4 uploads.

    Key signatures:
      • BPF modulation on current (hydraulic load pulsing at blade pass rate)
      • 1× rotational modulation as imbalance worsens
      • Mean current drops slightly (impeller efficiency degraded)
      • Range ↑ (load pulsation grows)
    """
    dev = sensor_deviation(upload_num, onset, lag=4, steepness=0.43)
    ts  = make_timestamps(datetime.now())

    rated = MOTOR['rated_current_a']    # 375 A
    f_sup = MOTOR['f_supply']           # 50 Hz

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    mid    = max(min((dev - 0.20) / 0.35, 1.0), 0.0)
    severe = max((dev - 0.80) / 0.20, 0.0)

    # ── Mean drops as impeller efficiency degrades ──
    # Max −8% at full fault (less fluid moved = less hydraulic work)
    dc_level = rated - dev * rated * 0.08
    dc_level = max(dc_level, rated * 0.88)

    # ── BPF current modulation — load pulsing at blade pass rate ──
    bpf_mod_amp = rated * dev * 0.055
    sig_bpf_mod = sinusoid(F_BPF, bpf_mod_amp)

    # ── 1× rotational modulation (hydraulic imbalance) ──
    rot_mod_amp = rated * mid * 0.035
    sig_rot_mod = sinusoid(F_ROT, rot_mod_amp)

    # ── Supply component (always present) ──
    sig_sup = sinusoid(f_sup, rated * 0.08)

    # ── Variance increase (range ↑) ──
    variance_scale = 1.0 + dev * 3.5
    noise_sigma_fault = rated * 0.004 * variance_scale

    signal = [dc_level + v + ss + sb + sr
              for v, ss, sb, sr
              in zip(gaussian_noise(noise_sigma_fault),
                     sig_sup, sig_bpf_mod, sig_rot_mod)]

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_level:.1f}A  '
                f'BPF_mod={bpf_mod_amp:.2f}A  ROT_mod={rot_mod_amp:.2f}A')


# ─────────────────────────────────────────────
# COMBINED GENERATE FUNCTION
# ─────────────────────────────────────────────
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> None:
    generate_acceleration(upload_num, onset, data_dir, logger)
    generate_audio(upload_num, onset, data_dir, logger)
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
