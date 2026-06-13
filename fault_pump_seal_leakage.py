"""
fault_pump_seal_leakage.py
==========================
Fault simulation: PUMP SEAL LEAKAGE

Physical description
--------------------
Mechanical seal degradation follows this progression:
  Stage 1 — Seal face wear: micro-leakage begins, fluid film breaks down
  Stage 2 — Developed leakage: visible drip/spray, air ingress begins
  Stage 3 — Air ingress cavitation-like: entrained air causes erratic flow
  Stage 4 — Seal failure: large leak, severe hydraulic load loss

This is the ONLY fault in the set where the mean current DECREASES first
before any other sensor responds. The hydraulic back-pressure on the impeller
drops as fluid leaks out of the sealed chamber — the motor sees less load.
This counter-intuitive early current drop, combined with audio hissing, is
the definitive ML fingerprint.

Sensor signatures
-----------------
Audio [LEAD, lag=0]
  • Hissing/spraying sound from leaking seal — high-frequency content
  • Fluid spray noise: broadband with energy above 150 Hz
  • Kurtosis ↑ (spray is intermittent at first — drips, then stream)
  • SPL rises moderately (82 → ~91 dB)
  • NO tonal frequency component — distinguishes from winding fault (100 Hz)
    and impeller damage (73.5 Hz)

Current [lag=1]
  • Mean DROPS first (reduced hydraulic load as fluid leaks)
  • Then FLUCTUATES as air ingress causes erratic loading
  • Range ↑↑ in stage 3 (air pockets cause torque spikes then drops)
  • Mean eventually stabilises low (~20% below rated)
  • This drop-then-fluctuate pattern is unique among all 11 faults

Acceleration [lag=3]
  • Initially minimal change (seal leakage doesn't vibrate the motor)
  • Stage 2–3: air ingress causes cavitation-like broadband vibration
  • Stage 4: hydraulic imbalance from uneven flow → 1× rotational grows
  • Rise is gradual and broadband — not impulsive like true cavitation
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

FAULT_NAME = 'pump_seal_leakage'

# Fluid spray frequency characteristics
F_SPRAY_LOW  = 160.0   # Hz — fluid spray broadband low end
F_SPRAY_MID  = 240.0   # Hz — fluid spray broadband mid
F_SPRAY_HIGH = 320.0   # Hz — fluid spray broadband high


# ─────────────────────────────────────────────
# AUDIO GENERATOR
# ─────────────────────────────────────────────
def generate_audio(upload_num: int, onset: int,
                   data_dir: str, logger) -> None:
    """
    Audio leads with lag=0.

    Stages:
      Drip (dev 0–0.25):   intermittent drip sounds — low kurtosis at first,
                            then isolated hiss bursts begin
      Spray (dev 0.25–0.6): continuous hissing — high-frequency broadband,
                             kurtosis drops (more continuous)
      Stream (dev > 0.6):   loud continuous spray, broadband floor elevated,
                             air ingress crackle begins
    """
    dev = sensor_deviation(upload_num, onset, lag=0, steepness=0.41)
    ts  = make_timestamps(datetime.now())

    base_db = MOTOR['audio_db']    # 82 dB

    # Healthy baseline
    noise_sigma = 1.2
    signal = [base_db + v for v in gaussian_noise(noise_sigma)]

    if dev < 0.01:
        save_max_min_csvs('audio', data_dir, ts, signal)
        return

    drip   = min(dev / 0.25, 1.0)
    spray  = max(min((dev - 0.25) / 0.35, 1.0), 0.0)
    stream = max((dev - 0.60) / 0.40, 0.0)

    # ── SPL rise (moderate — seal noise, not motor noise) ──
    db_level = base_db + drip * 2.5 + spray * 5.0 + stream * 3.5

    # ── High-frequency fluid spray bands ──
    spray_low  = base_db * 0.008 * (spray * 0.6 + stream)
    spray_mid  = base_db * 0.012 * (spray + stream * 0.8)
    spray_high = base_db * 0.009 * (spray * 0.4 + stream * 0.6)

    sig_spray_l = sinusoid(F_SPRAY_LOW,  spray_low,
                           phase=random.uniform(0, 2 * math.pi))
    sig_spray_m = sinusoid(F_SPRAY_MID,  spray_mid,
                           phase=random.uniform(0, 2 * math.pi))
    sig_spray_h = sinusoid(F_SPRAY_HIGH, spray_high,
                           phase=random.uniform(0, 2 * math.pi))

    # ── Broadband noise floor ──
    broadband_sigma = 1.2 + dev * 3.8
    noise_broadband = gaussian_noise(broadband_sigma)

    signal = [db_level * 0.04 + v + sl + sm + sh
              for v, sl, sm, sh
              in zip(noise_broadband,
                     sig_spray_l, sig_spray_m, sig_spray_h)]

    # ── Drip/burst events (Stage 1: intermittent, high kurtosis) ──
    if dev > 0.05 and drip > 0:
        drip_rate = 0.8 + drip * 4.0     # slow drip → fast drip
        drip_mag  = db_level * 0.12 * drip
        signal = add_impulses(signal, rate=drip_rate,
                              magnitude=drip_mag, decay=0.60)

    # ── Air ingress crackle (Stage 3: resembles mild cavitation) ──
    if stream > 0.10:
        crackle_rate = 2.0 + stream * 8.0
        crackle_mag  = db_level * 0.08 * stream
        signal = add_impulses(signal, rate=crackle_rate,
                              magnitude=crackle_mag, decay=0.45)

    signal = [min(s, 98.0) for s in signal]

    save_max_min_csvs('audio', data_dir, ts, signal)
    logger.info(f'  [audio]   dev={dev:.3f}  SPL≈{db_level:.1f}dB  '
                f'stage: drip={drip:.2f} spray={spray:.2f} stream={stream:.2f}')


# ─────────────────────────────────────────────
# CURRENT GENERATOR
# ─────────────────────────────────────────────
def generate_current(upload_num: int, onset: int,
                     data_dir: str, logger) -> None:
    """
    Current lags audio by 1 upload.

    Unique counter-intuitive profile — the only fault where mean drops first:
      Stage 1 (dev 0–0.30): mean drops as hydraulic back-pressure falls
      Stage 2 (dev 0.30–0.65): fluctuates as air ingress causes erratic loading
                                Range ↑↑ — torque spikes as air pockets pass
      Stage 3 (dev > 0.65): settles ~18–22% below rated
                             (motor running partially unloaded)

    The drop magnitude and then range increase is the clearest ML differentiator
    between seal leakage and all other faults.
    """
    dev = sensor_deviation(upload_num, onset, lag=1, steepness=0.41)
    ts  = make_timestamps(datetime.now())

    rated = MOTOR['rated_current_a']    # 375 A
    f_sup = MOTOR['f_supply']           # 50 Hz
    f_rot = MOTOR['f_rot']             # 12.25 Hz

    # Healthy baseline
    noise_sigma = rated * 0.004
    signal = [rated + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_sup, rated * 0.08))]

    if dev < 0.01:
        save_max_min_csvs('current', data_dir, ts, signal)
        return

    drop_phase      = min(dev / 0.30, 1.0)
    fluctuate_phase = max(min((dev - 0.30) / 0.35, 1.0), 0.0)
    settled_phase   = max((dev - 0.65) / 0.35, 0.0)

    # ── Mean current drops then stabilises low ──
    # Drop: −22% of rated at full seal failure
    dc_drop    = rated * 0.22 * drop_phase
    # Partial recovery during air ingress (erratic load)
    dc_recover = rated * 0.04 * fluctuate_phase
    dc_level   = rated - dc_drop + dc_recover
    dc_level   = max(dc_level, rated * 0.75)   # floor: motor still running

    # ── Variance: spikes up during air ingress phase ──
    # Air pockets cause sudden load drops and recoveries
    variance_scale = 1.0 + fluctuate_phase * 7.0 + settled_phase * 2.5
    noise_sigma_fault = rated * 0.004 * variance_scale

    # ── Supply frequency (always present) ──
    sig_sup = sinusoid(f_sup, rated * 0.08)

    # ── Rotational modulation grows at air ingress (erratic hydraulic load) ──
    rot_mod_amp = rated * 0.020 * fluctuate_phase
    sig_rot     = sinusoid(f_rot, rot_mod_amp)

    signal = [dc_level + v + ss + sr
              for v, ss, sr
              in zip(gaussian_noise(noise_sigma_fault), sig_sup, sig_rot)]

    # ── Air pocket torque spikes during fluctuation phase ──
    if fluctuate_phase > 0.15:
        spike_rate = 1.5 + fluctuate_phase * 6.0
        # Torque spikes can be positive (liquid slug) or negative (air pocket)
        spike_mag  = rated * 0.18 * fluctuate_phase
        n = len(signal)
        fs = SAMPLE_RATE
        interval = max(1, int(fs / spike_rate))
        i = random.randint(0, interval)
        while i < n:
            direction = random.choice([1.0, -1.0])  # liquid slug or air pocket
            mag = direction * spike_mag * random.uniform(0.5, 1.5)
            for j in range(i, min(i + int(0.02 * fs), n)):
                signal[j] += mag * (0.72 ** (j - i))
            i += interval + random.randint(-interval // 3, interval // 3)

    save_max_min_csvs('current', data_dir, ts, signal)
    logger.info(f'  [current] dev={dev:.3f}  DC={dc_level:.1f}A  '
                f'(rated={rated:.0f}A  drop={dc_drop:.1f}A)  '
                f'variance_scale={variance_scale:.2f}')


# ─────────────────────────────────────────────
# ACCELERATION GENERATOR
# ─────────────────────────────────────────────
def generate_acceleration(upload_num: int, onset: int,
                           data_dir: str, logger) -> None:
    """
    Acceleration lags audio by 3 uploads.

    Key signatures:
      • Stage 1: near-zero change (seal leaks silently, no mechanical vibration)
      • Stage 2: air ingress causes broadband vibration rise (cavitation-like
                 but less impulsive — distinguishable by lower kurtosis)
      • Stage 3: hydraulic imbalance → 1× rotational grows
      • Overall: slowest and mildest acceleration response of all 11 faults
    """
    dev = sensor_deviation(upload_num, onset, lag=3, steepness=0.41)
    ts  = make_timestamps(datetime.now())

    base_g = MOTOR['accel_rms_g']    # 0.50 g
    f_rot  = MOTOR['f_rot']          # 12.25 Hz

    # Healthy baseline
    noise_sigma = base_g * 0.10
    signal = [base_g * 0.04 + v for v in gaussian_noise(noise_sigma)]
    signal = [s + a for s, a in zip(signal, sinusoid(f_rot, base_g * 0.28))]

    if dev < 0.01:
        save_max_min_csvs('acceleration', data_dir, ts, signal)
        return

    air_ingress = max(min((dev - 0.25) / 0.40, 1.0), 0.0)
    hydraulic   = max((dev - 0.65) / 0.35, 0.0)

    # ── Rotational component (always present, grows with hydraulic imbalance) ──
    rot_amp = base_g * (0.28 + hydraulic * 0.55)
    sig_rot = sinusoid(f_rot, rot_amp)

    # ── Broadband noise: air ingress turbulence ──
    # Milder than cavitation — air ingress is less violent than bubble collapse
    broadband_sigma = base_g * (0.10 + air_ingress * 0.55 + hydraulic * 0.30)
    noise_fault = gaussian_noise(broadband_sigma)

    signal = [base_g * 0.04 + v + r
              for v, r in zip(noise_fault, sig_rot)]

    # ── Air pocket impulses (less impulsive than cavitation) ──
    # Lower kurtosis than pump_cavitation — this is a key distinguisher
    if air_ingress > 0.20:
        air_rate = 1.5 + air_ingress * 6.0
        air_mag  = base_g * air_ingress * 0.35    # significantly lower than cavitation
        signal = add_impulses(signal, rate=air_rate,
                              magnitude=air_mag, decay=0.68)

    rms_est = (sum(s**2 for s in signal) / len(signal)) ** 0.5
    save_max_min_csvs('acceleration', data_dir, ts, signal)
    logger.info(f'  [accel]   dev={dev:.3f}  RMS≈{rms_est:.3f}g  '
                f'rot={rot_amp:.3f}g  air_ingress={air_ingress:.2f}  '
                f'hydraulic={hydraulic:.2f}')


# ─────────────────────────────────────────────
# COMBINED GENERATE FUNCTION
# ─────────────────────────────────────────────
def generate_all(upload_num: int, onset: int,
                 data_dir: str, logger) -> None:
    generate_audio(upload_num, onset, data_dir, logger)
    generate_current(upload_num, onset, data_dir, logger)
    generate_acceleration(upload_num, onset, data_dir, logger)


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == '__main__':
    run_fault_simulation(
        fault_name    = FAULT_NAME,
        generate_fn   = generate_all,
        sleep_seconds = 30,
    )
