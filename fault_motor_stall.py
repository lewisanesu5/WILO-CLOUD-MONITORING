"""
fault_motor_stall.py
====================
Fault simulation: MOTOR STALL

Physical description
--------------------
A stall occurs when the rotor is forced to stop or slow dramatically while the
supply is still energised.  Back-EMF collapses → current surges to near
Locked-Rotor Current (LRC ≈ 6.5 × FLA = ~2 438 A).

Sensor signatures
-----------------
Current  [LEAD, lag=0]
  • Pre-stall struggle phase: current rises as motor fights the load
  • Full-stall phase: sustained surge to 2 000–2 500 A
  • Dominant frequency: 50 Hz (supply) locks in; sidebands vanish
  • Skewness ↑ at onset (spike shape), kurtosis ↑ during onset
  • Mean ↑↑↑ once stalled

Acceleration [lag=1]
  • Struggle phase: vibration rises (motor fighting load)
  • Full-stall: vibration DROPS (rotor stationary → no rotating imbalance)
  • Non-monotonic — this dip is a key ML fingerprint
  • Top frequency shifts from 12.25 Hz to 50 Hz harmonics during struggle

Audio [lag=2]
  • Loud 50 Hz hum dominates
  • Mean dB ↑↑ (up to 105–110 dB at full stall)
  • Harmonic content at 100 Hz, 150 Hz
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

FAULT_NAME = 'motor_stall'


# ─────────────────────────────────────────────
# CURRENT GENERATOR
# ─────────────────────────────────────────────
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current leads with lag=0.

    Stages:
      dev_c < 0.15  → normal operation
      0.15–0.45     → struggle: current climbs, supply-freq component grows
      0.45–0.75     → near-stall: surge approaching LRC
      > 0.75        → full stall: current locked at ~2 200–2 450 A
    """
    dev = sensor_deviation(upload_num, onset, lag=0, steepness=0.50)
    ts  = make_timestamps(datetime.now())

    rated   = MOTOR['rated_current_a']          # 375 A
    lrc     = rated * MOTOR['locked_rotor_mult'] # ~2 438 A
    f_sup   = MOTOR['f_supply']                 # 50 Hz
    f_rot   = MOTOR['f_rot']                    # 12.25 Hz

    # ── baseline: full-load AC current ──
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal,
              sinusoid(f_sup, rated * 0.08))]            # supply ripple

    if dev < 0.01:
        # Pure healthy operation
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    # ── struggle phase (dev 0–0.50): rising current ──
    struggle_factor = min(dev / 0.50, 1.0)
    stall_factor    = max((dev - 0.50) / 0.50, 0.0)

    # Current rises toward LRC
    dc_rise   = rated + struggle_factor * (lrc * 0.70 - rated)
    dc_stall  = lrc * 0.85 + stall_factor * (lrc * 0.15)
    dc_level  = dc_rise if stall_factor == 0 else dc_stall

    # Supply-frequency component grows (back-EMF collapse)
    sup_amp   = rated * 0.08 + dev * rated * 1.20
    sig_sup   = sinusoid(f_sup, sup_amp)

    # Rotational sideband fades as rotor slows
    rot_amp   = rated * 0.05 * (1.0 - dev)
    sig_rot   = sinusoid(f_rot, rot_amp)

    # Struggle impulses at onset (inrush-like spikes)
    if dev < 0.45:
        impulse_mag = (lrc - rated) * 0.25 * struggle_factor
        signal = add_impulses(signal, rate=f_sup, magnitude=impulse_mag,
                              decay=0.60)

    # Noise grows with current magnitude
    noise_sigma_fault = dc_level * 0.012
    signal = [dc_level + v + ss + sr
              for v, ss, sr
              in zip(gaussian_noise(noise_sigma_fault), sig_sup, sig_rot)]

    # Hard clamp to LRC
    signal = [min(s, lrc * 1.05) for s in signal]

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_level:.0f}A  '
                f'struggle={struggle_factor:.2f}  stall={stall_factor:.2f}')


# ─────────────────────────────────────────────
# ACCELERATION GENERATOR
# ─────────────────────────────────────────────
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration lags current by 1 upload.

    Non-monotonic profile — key ML fingerprint:
      dev_a < 0.40  → vibration RISES (motor fighting load)
      dev_a 0.40–0.60 → vibration PEAKS
      dev_a > 0.60  → vibration DROPS toward near-zero (rotor stationary)
    """
    dev = sensor_deviation(upload_num, onset, lag=1, steepness=0.50)
    ts  = make_timestamps(datetime.now())

    base_accel = MOTOR['accel_rms_g']    # 0.50 g
    f_rot      = MOTOR['f_rot']          # 12.25 Hz
    f_sup      = MOTOR['f_supply']       # 50 Hz

    # Healthy baseline
    noise_sigma = base_accel * 0.08
    signal = [base_accel * 0.05 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_accel * 0.30))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    # ── struggle phase: vibration rises ──
    peak_factor  = min(dev / 0.40, 1.0)           # 0 → 1 during struggle
    # ── stall phase: vibration falls back ──
    decay_factor = max((dev - 0.40) / 0.60, 0.0)  # 0 → 1 as rotor stops

    # Net vibration amplitude: rises then falls
    # Peak at ~3× base, collapses to ~0.1× base at full stall
    struggle_amp = base_accel * (1.0 + peak_factor * 2.80)
    stall_amp    = struggle_amp * (1.0 - decay_factor * 0.90)
    net_amp      = max(stall_amp, base_accel * 0.10)

    # During struggle: rotational + supply harmonics
    rot_component  = sinusoid(f_rot, net_amp * 0.50)
    sup_component  = sinusoid(f_sup, net_amp * 0.25 * dev)
    sup2_component = sinusoid(f_sup * 2, net_amp * 0.10 * dev)

    noise_sigma_fault = net_amp * 0.12
    signal = [net_amp * 0.05 + v + r + s + s2
              for v, r, s, s2
              in zip(gaussian_noise(noise_sigma_fault),
                     rot_component, sup_component, sup2_component)]

    # Add struggle impulses (torque shocks)
    if 0.10 < dev < 0.55:
        impulse_mag = net_amp * 0.60 * peak_factor
        signal = add_impulses(signal, rate=f_rot * 0.5,
                              magnitude=impulse_mag, decay=0.80)

    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev={dev:.3f}  net_amp={net_amp:.3f}g  '
                f'peak_factor={peak_factor:.2f}  decay={decay_factor:.2f}')


# ─────────────────────────────────────────────
# AUDIO GENERATOR
# ─────────────────────────────────────────────
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio lags current by 2 uploads.

    Characteristics:
      • Loud 50 Hz fundamental hum dominates
      • Harmonics at 100 Hz, 150 Hz grow
      • SPL rises from 82 dB to 105–110 dB at full stall
      • Mean dB ↑↑, top frequency = 50 Hz
    """
    dev = sensor_deviation(upload_num, onset, lag=2, steepness=0.50)
    ts  = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB
    f_sup   = MOTOR['f_supply']    # 50 Hz

    # Healthy baseline: broadband mechanical noise
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]
    # Low-level 50 Hz + 100 Hz always present
    signal = [s + a + b
              for s, a, b
              in zip(signal,
                     sinusoid(f_sup,     base_db * 0.03),
                     sinusoid(f_sup * 2, base_db * 0.01))]

    if dev < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    # SPL rises dramatically — stalled motor is very loud
    max_db_rise = 26.0    # 82 → ~108 dB at full stall
    db_level    = base_db + dev * max_db_rise

    # 50 Hz hum amplitude scales with current surge (proportional)
    hum_50  = (db_level - base_db) * 0.65
    hum_100 = (db_level - base_db) * 0.25
    hum_150 = (db_level - base_db) * 0.10

    sig_50  = sinusoid(f_sup,       hum_50)
    sig_100 = sinusoid(f_sup * 2,   hum_100)
    sig_150 = sinusoid(f_sup * 3,   hum_150)

    noise_sigma_fault = 1.5 + dev * 2.5
    signal = [db_level * 0.05 + v + s1 + s2 + s3
              for v, s1, s2, s3
              in zip(gaussian_noise(noise_sigma_fault),
                     sig_50, sig_100, sig_150)]

    # Clamp to physically realistic ceiling
    signal = [min(s, 115.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL≈{db_level:.1f}dB  '
                f'hum_50={hum_50:.1f}  hum_100={hum_100:.1f}')


# ─────────────────────────────────────────────
# COMBINED GENERATE FUNCTION
# ─────────────────────────────────────────────
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> None:
    generate_current(upload_num, onset, data_dir, logger)
    generate_acceleration(upload_num, onset, data_dir, logger)
    generate_audio(upload_num, onset, data_dir, logger)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    run_fault_simulation(
        fault_name    = FAULT_NAME,
        generate_fn   = generate_all,
        sleep_seconds = 30,
    )
