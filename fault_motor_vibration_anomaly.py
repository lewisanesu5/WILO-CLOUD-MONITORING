"""
fault_motor_vibration_anomaly.py
=================================
Fault simulation: MOTOR VIBRATION ANOMALY

Physical description
--------------------
A general broadband vibration increase without a single dominant frequency.
Common causes: loose mounting bolts, structural resonance, worn motor mounts,
unbalanced accessory loads, or a combination of minor defects that don't
individually produce a clean spectral signature.

This fault is deliberately distinct from shaft misalignment (which has clean
1× and 2× peaks) and bearing failure (which has BPFO/BPFI peaks).
Here the energy is spread across the spectrum — the ML model must learn to
detect rising broadband RMS rather than a specific frequency component.

Sensor signatures
-----------------
Acceleration [LEAD, lag=0]
  • Broadband RMS rises — no single dominant frequency
  • Random burst character: short-duration energy packets
  • Kurtosis rises then plateaus (impulsive character at onset, then sustained)
  • Range ↑↑, Mean ↑, top 5 frequencies spread across 5–150 Hz band
  • Structural resonance peaks at natural frequency of frame (~35–60 Hz typical)

Current [lag=3]
  • Load torque fluctuates as vibration causes coupling irregularities
  • Range ↑ slightly — current variance increases
  • No strong spectral component — distinguishes this from misalignment
  • Mean stays close to rated (load is same, just noisier mechanical path)

Audio [lag=2]
  • Structural rattle and resonance noise — broadband character
  • Intermittent knock or rattle events (loose bolt impacts)
  • Mean dB ↑ moderately (not as dramatic as stall)
  • Kurtosis ↑ (rattling produces impulsive audio content)
  • No dominant single frequency — key differentiator from electrical faults
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

FAULT_NAME = 'motor_vibration_anomaly'

ACCEL_LAG   = random.randint(0, 1)
AUDIO_LAG   = random.randint(1, 3)
CURRENT_LAG = random.randint(2, 4)

# Structural resonance frequency (motor frame natural frequency)
# Typical for 355-frame TEFC on steel baseplate
F_RESONANCE_1 = 38.5   # Hz — first bending mode
F_RESONANCE_2 = 71.0   # Hz — second bending mode
F_RESONANCE_3 = 112.0  # Hz — third bending mode


# ─────────────────────────────────────────────
# ACCELERATION GENERATOR
# ─────────────────────────────────────────────
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration leads with lag=0.

    Key characteristics:
      • Broadband RMS growth — not frequency-specific
      • Structural resonance bursts at 38.5, 71, 112 Hz
      • Random burst-mode energy packets (loose component impacts)
      • Kurtosis ↑ early (burst character), then stabilises at high level
      • By upload 50: RMS ~4–6× baseline, highly erratic
    """
    dev = sensor_deviation(upload_num, onset, lag=ACCEL_LAG, steepness=0.42)
    ts  = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g
    f_rot  = MOTOR['f_rot']          # 12.25 Hz

    # ── Healthy baseline ──
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    # Low-level rotational component always present
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_g * 0.28))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    # ── Broadband RMS growth ──
    # 5× RMS increase at full fault
    rms_multiplier = 1.0 + dev * 4.80
    broadband_sigma = base_g * rms_multiplier * 0.55

    # ── Structural resonance components — amplitude grows with dev ──
    res1_amp = base_g * dev * 1.20   # 38.5 Hz
    res2_amp = base_g * dev * 0.80   # 71.0 Hz
    res3_amp = base_g * dev * 0.45   # 112.0 Hz

    sig_res1 = sinusoid(F_RESONANCE_1, res1_amp,
                        phase=random.uniform(0, 2 * math.pi))
    sig_res2 = sinusoid(F_RESONANCE_2, res2_amp,
                        phase=random.uniform(0, 2 * math.pi))
    sig_res3 = sinusoid(F_RESONANCE_3, res3_amp,
                        phase=random.uniform(0, 2 * math.pi))

    # Rotational component stays (it's always there in a running motor)
    sig_rot  = sinusoid(f_rot, base_g * 0.28)

    # ── Broadband noise floor ──
    noise_fault = gaussian_noise(broadband_sigma)

    signal = [v + r + r1 + r2 + r3
              for v, r, r1, r2, r3
              in zip(noise_fault, sig_rot, sig_res1, sig_res2, sig_res3)]

    # ── Random burst events — loose component impacts ──
    # Bursts occur more frequently as fault progresses
    if dev > 0.08:
        burst_rate     = 2.0 + dev * 8.0     # 2–10 bursts/sec
        burst_mag      = base_g * dev * 3.50
        signal = add_impulses(signal, rate=burst_rate,
                              magnitude=burst_mag, decay=0.75)

    # ── Amplitude modulation — load path irregularity ──
    # Slow modulation at sub-rotational frequency (structural resonance)
    if dev > 0.20:
        mod_depth = dev * 0.35
        mod_freq  = 2.5   # Hz — slow wobble
        n = len(signal)
        signal = [signal[i] * (1.0 + mod_depth *
                                math.sin(2 * math.pi * mod_freq * i / SAMPLE_RATE))
                  for i in range(n)]

    save_max_min_csvs('acceleration', data_dir, ts, signal)
    rms_est = (sum(s ** 2 for s in signal) / len(signal)) ** 0.5
    logger.info(f'  [accel]   dev={dev:.3f}  RMS≈{rms_est:.3f}g  '
                f'res1={res1_amp:.3f}g  burst_rate≈{2.0+dev*8.0:.1f}/s'
                if dev > 0.01 else f'  [accel]   NORMAL  dev={dev:.3f}')


# ─────────────────────────────────────────────
# AUDIO GENERATOR
# ─────────────────────────────────────────────
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio lags acceleration by 2 uploads.

    Characteristics:
      • Structural rattle — broadband frequency content
      • Intermittent knock events from loose hardware
      • Mean dB rises moderately (82 → ~95 dB at full fault)
      • Kurtosis ↑ due to impulsive knocking character
      • No single dominant frequency (key differentiator)
    """
    dev = sensor_deviation(upload_num, onset, lag=AUDIO_LAG, steepness=0.42)
    ts  = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB

    # Healthy baseline
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]

    if dev < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    # ── SPL rise: broadband, not tonal ──
    max_db_rise = 13.0    # 82 → ~95 dB at full fault (moderate, not dramatic)
    db_level    = base_db + dev * max_db_rise

    # Broadband noise floor rises
    broadband_sigma = 1.2 + dev * 4.5
    noise_broadband = gaussian_noise(broadband_sigma)

    # Structural resonances also appear in audio (airborne radiation)
    res1_audio = base_db * 0.012 * dev   # 38.5 Hz air-radiated
    res2_audio = base_db * 0.008 * dev   # 71.0 Hz
    sig_res1   = sinusoid(F_RESONANCE_1, res1_audio)
    sig_res2   = sinusoid(F_RESONANCE_2, res2_audio)

    signal = [db_level * 0.04 + v + r1 + r2
              for v, r1, r2
              in zip(noise_broadband, sig_res1, sig_res2)]

    # ── Knock/rattle impacts — audible loose hardware ──
    if dev > 0.10:
        knock_rate = 1.5 + dev * 5.0    # 1.5–6.5 knocks/sec
        knock_mag  = db_level * 0.18 * dev
        signal = add_impulses(signal, rate=knock_rate,
                              magnitude=knock_mag, decay=0.70)

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL≈{db_level:.1f}dB  '
                f'broadband_σ={broadband_sigma:.2f}')


# ─────────────────────────────────────────────
# CURRENT GENERATOR
# ─────────────────────────────────────────────
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current lags acceleration by 3 uploads.

    Characteristics:
      • Mean stays close to rated — mechanical vibration doesn't strongly
        change average electrical load
      • Range ↑ — load torque fluctuates with vibration
      • No strong spectral component — key ML differentiator from misalignment
      • Slight variance increase due to coupling irregularities
    """
    dev = sensor_deviation(upload_num, onset, lag=CURRENT_LAG, steepness=0.42)
    ts  = make_timestamps(datetime.now())

    rated  = MOTOR['rated_current_a']    # 375 A
    f_rot  = MOTOR['f_rot']              # 12.25 Hz
    f_sup  = MOTOR['f_supply']           # 50 Hz

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    # ── Slight mean rise from load fluctuation (not dramatic) ──
    dc_rise    = rated + dev * rated * 0.06   # max +6% mean current
    # ── Range increase: load torque is irregular ──
    variance_scale = 1.0 + dev * 4.5
    noise_sigma_fault = rated * 0.004 * variance_scale

    # Supply component stays; no new strong frequency component
    sig_sup = sinusoid(f_sup, rated * 0.08)
    sig_rot = sinusoid(f_rot, rated * 0.015)  # very small rotational

    # Broadband current noise (vibration-induced load noise)
    broadband_noise = gaussian_noise(noise_sigma_fault)

    signal = [dc_rise + v + ss + sr
              for v, ss, sr
              in zip(broadband_noise, sig_sup, sig_rot)]

    # ── Occasional load spikes from structural impacts ──
    if dev > 0.25:
        spike_rate = 1.0 + dev * 3.0
        spike_mag  = rated * 0.08 * dev
        signal = add_impulses(signal, rate=spike_rate,
                              magnitude=spike_mag, decay=0.65)

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_rise:.1f}A  '
                f'noise_σ={noise_sigma_fault:.2f}A')


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
