"""
fault_motor_bearing_failure.py
==============================
Simulates progressive bearing failure on the Havells MHPE355LB8.

Physical progression:
  Stage 1 (early)  : Lubrication film breakdown → micro-pitting
                     Sub-surface fatigue, barely detectable
  Stage 2 (mid)    : Surface spalling begins → periodic impulses at BPFO/BPFI
                     Kurtosis rises sharply in acceleration
  Stage 3 (late)   : Spall grows, metal debris → broadband noise + heat
                     All sensors deviating, current rises from extra friction load
  Stage 4 (critical): Bearing race fracture, motor seizure imminent

Sensor lead/lag:
  Acceleration → leads (mounted on bearing housing)
  Audio        → lags by 3 uploads
  Current      → lags by 5 uploads

Key statistical signatures for ML:
  - Acceleration: kurtosis ↑↑↑ (most sensitive), skewness ↑, BPFO/BPFI in top freqs
  - Audio:        kurtosis ↑↑, top freq = BPFO (52.3 Hz)
  - Current:      mean ↑ slightly, spectral sidebands at f_supply ± BPFO
"""

import math, random
from datetime import datetime, timedelta
from base_motor import (MOTOR, N_SAMPLES, SAMPLE_RATE, TOTAL_UPLOADS,
                         LOCAL_DATA_DIR, sensor_deviation, gaussian_noise,
                         sinusoid, add_impulses, save_max_min_csvs,
                         make_timestamps, run_fault_simulation)

FAULT_NAME = 'motor_bearing_failure'

# Bearing characteristic frequencies (Hz)
BPFO = MOTOR['bpfo']   # 52.3 Hz — outer race
BPFI = MOTOR['bpfi']   # 72.7 Hz — inner race
BSF  = MOTOR['bsf']    #  9.1 Hz — ball spin
FTF  = MOTOR['ftf']    #  4.4 Hz — cage

ACCEL_LAG   = random.randint(0, 1)
AUDIO_LAG   = random.randint(2, 4)
CURRENT_LAG = random.randint(4, 6)



def generate(upload_num: int, onset: int, data_dir: str, logger):
    d_accel   = sensor_deviation(upload_num, onset, ACCEL_LAG,   steepness=0.40)
    d_audio   = sensor_deviation(upload_num, onset, AUDIO_LAG,   steepness=0.38)
    d_current = sensor_deviation(upload_num, onset, CURRENT_LAG, steepness=0.35)

    fs = SAMPLE_RATE
    n  = N_SAMPLES
    now = datetime.now()
    ts  = make_timestamps(now, n, fs)

    # ── ACCELERATION ────────────────────────────────────────────────────────
    # Healthy: broadband vibration + 1× rotational + slight 50 Hz from supply
    accel = [MOTOR['accel_rms_g'] + random.gauss(0, 0.06) for _ in range(n)]
    rot   = sinusoid(MOTOR['f_rot'], 0.15)                 # 1× rotational
    sup50 = sinusoid(MOTOR['f_supply'], 0.04)              # supply coupling
    accel = [accel[i] + rot[i] + sup50[i] for i in range(n)]

    if d_accel > 0.01:
        # Impulse rate grows with deviation: 1 per revolution early, more at failure
        # At 735 RPM → ~12.25 impulses/sec at BPFO; grows with d
        impulse_rate_bpfo = BPFO * (0.05 + d_accel * 0.95)   # partial at onset
        impulse_rate_bpfi = BPFI * (0.02 + d_accel * 0.5)
        impulse_mag_bpfo  = d_accel * 3.5   # g — grows to 3.5g at critical
        impulse_mag_bpfi  = d_accel * 1.8

        accel = add_impulses(accel, impulse_rate_bpfo,
                             impulse_mag_bpfo, decay=0.78)
        accel = add_impulses(accel, impulse_rate_bpfi,
                             impulse_mag_bpfi, decay=0.72)

        # Add BPFO sinusoidal component (secondary to impulses)
        bpfo_sin = sinusoid(BPFO, d_accel * 0.6)
        bsf_sin  = sinusoid(BSF,  d_accel * 0.3)
        accel = [accel[i] + bpfo_sin[i] + bsf_sin[i] for i in range(n)]

        # Broadband noise floor rises with bearing degradation (heat + debris)
        noise_extra = gaussian_noise(d_accel * 0.4, n)
        accel = [accel[i] + noise_extra[i] for i in range(n)]

    save_max_min_csvs('acceleration', data_dir, ts, accel)
    logger.info(f'  Accel  dev={d_accel:.3f}  '
                f'peak={max(accel):.3f}g  rms={math.sqrt(sum(v**2 for v in accel)/n):.3f}g')

    # ── AUDIO ────────────────────────────────────────────────────────────────
    # Healthy: broadband machine hum, dominant 50 Hz, harmonics
    audio = [MOTOR['audio_db'] + random.gauss(0, 1.2) for _ in range(n)]
    h50   = sinusoid(50,  4.0)    # 50 Hz fundamental
    h100  = sinusoid(100, 1.8)    # 2nd harmonic
    h150  = sinusoid(150, 0.9)    # 3rd harmonic
    audio = [audio[i] + h50[i] + h100[i] + h150[i] for i in range(n)]

    if d_audio > 0.01:
        # High-pitched whine at BPFO and BPFI — characteristic bearing squeal
        bpfo_whine = sinusoid(BPFO, d_audio * 8.0)     # dB amplitude
        bpfi_whine = sinusoid(BPFI, d_audio * 5.0)
        bsf_whine  = sinusoid(BSF,  d_audio * 2.5)
        audio = [audio[i] + bpfo_whine[i] + bpfi_whine[i] + bsf_whine[i]
                 for i in range(n)]

        # Crackling impulse noise from spall impacts (high kurtosis)
        crackle_rate = 20 + d_audio * 180     # Hz equivalent rate
        audio = add_impulses(audio, crackle_rate, d_audio * 6.0, decay=0.60)

        # Broadband noise floor rise (metal debris, friction)
        audio = [audio[i] + random.gauss(0, d_audio * 2.5) for i in range(n)]

    save_max_min_csvs('audio', data_dir, ts, audio)
    logger.info(f'  Audio  dev={d_audio:.3f}  '
                f'peak={max(audio):.2f}dB  mean={sum(audio)/n:.2f}dB')

    # ── CURRENT ──────────────────────────────────────────────────────────────
    # Healthy: sinusoidal draw at 50 Hz, amplitude = rated current
    I_rated = MOTOR['rated_current_a']
    current = [I_rated + random.gauss(0, 2.5) for _ in range(n)]
    sup_sin = sinusoid(50, I_rated * 0.08)    # AC ripple component
    current = [current[i] + sup_sin[i] for i in range(n)]

    if d_current > 0.01:
        # Extra friction load from damaged bearing → current increases
        # At critical: ~8–12% above rated
        extra_load = I_rated * d_current * 0.12
        current = [current[i] + extra_load for i in range(n)]

        # Spectral sidebands at f_supply ± BPFO (motor current signature analysis)
        sideband_lo = sinusoid(50 - BPFO, d_current * I_rated * 0.025)
        sideband_hi = sinusoid(50 + BPFO, d_current * I_rated * 0.025)
        current = [current[i] + sideband_lo[i] + sideband_hi[i]
                   for i in range(n)]

        # Small random spikes from load transients
        current = add_impulses(current, 2.0, d_current * 15.0, decay=0.50)

    save_max_min_csvs('current', data_dir, ts, current)
    logger.info(f'  Current dev={d_current:.3f}  '
                f'peak={max(current):.1f}A  mean={sum(current)/n:.1f}A')


if __name__ == '__main__':
    run_fault_simulation(FAULT_NAME, generate,
                          sleep_seconds=30,
                          data_dir=LOCAL_DATA_DIR)
