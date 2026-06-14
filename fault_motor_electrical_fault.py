"""
fault_motor_electrical_fault.py
================================
Simulates a broken rotor bar / stator winding asymmetry fault.

Physical progression:
  Broken rotor bars interrupt current paths in the squirrel cage.
  This creates:
    - Sidebands in current spectrum at f_supply ± 2·s·f_supply
      where s = slip = 0.02  →  sidebands at 48 Hz and 52 Hz
    - Torque pulsations at 2×slip frequency → vibration
    - Increased magnetic noise at 2× supply (100 Hz)
    - As more bars crack, asymmetry worsens → phase imbalance → heating

  Progression: hairline crack → partial break → full bar loss → adjacent bar crack

Sensor lead/lag:
  Current      → leads (electrical symptom is first)
  Audio        → lags by 2 uploads (magnetic hum becomes audible)
  Acceleration → lags by 3 uploads (torque pulsation → vibration)

Key statistical signatures:
  - Current:      skewness ↑, top freqs include 48 Hz & 52 Hz sidebands, kurtosis ↑
  - Audio:        100 Hz dominant (2× supply), mean dB ↑
  - Acceleration: range ↑, kurtosis ↑ (torque pulses), 2× slip freq component
"""

import math, random
from datetime import datetime
from base_motor import (MOTOR, N_SAMPLES, SAMPLE_RATE, TOTAL_UPLOADS,
                         LOCAL_DATA_DIR, sensor_deviation, gaussian_noise,
                         sinusoid, add_impulses, amplitude_modulate,
                         save_max_min_csvs, make_timestamps,
                         run_fault_simulation)

FAULT_NAME = 'motor_electrical_fault'

SLIP        = MOTOR['slip']           # 0.02
F_SUPPLY    = MOTOR['f_supply']       # 50 Hz
F_SIDEBAND_LO = F_SUPPLY - 2 * SLIP * F_SUPPLY   # 48 Hz
F_SIDEBAND_HI = F_SUPPLY + 2 * SLIP * F_SUPPLY   # 52 Hz
F_2SLIP     = 2 * SLIP * F_SUPPLY    # 2 Hz - torque ripple
F_ROT       = MOTOR['f_rot']         # 12.25 Hz

CURRENT_LAG = random.randint(0, 1)
AUDIO_LAG   = random.randint(1, 3)
ACCEL_LAG   = random.randint(2, 4)



def generate(upload_num: int, onset: int, data_dir: str, logger):
    d_current = sensor_deviation(upload_num, onset, CURRENT_LAG, steepness=0.42)
    d_audio   = sensor_deviation(upload_num, onset, AUDIO_LAG,   steepness=0.40)
    d_accel   = sensor_deviation(upload_num, onset, ACCEL_LAG,   steepness=0.38)

    fs  = SAMPLE_RATE
    n   = N_SAMPLES
    ts  = make_timestamps(datetime.now(), n, fs)
    I_r = MOTOR['rated_current_a']

    # -- CURRENT --------------------------------------------------------------
    # Healthy: 50 Hz AC draw, small harmonic distortion (THD ~3%)
    current = [I_r + random.gauss(0, 2.5) for _ in range(n)]
    fund    = sinusoid(F_SUPPLY, I_r * 0.08)   # fundamental ripple
    thd3    = sinusoid(150, I_r * 0.008)        # 3rd harmonic (healthy THD)
    current = [current[i] + fund[i] + thd3[i] for i in range(n)]

    if d_current > 0.01:
        # Rotor bar sidebands grow proportional to deviation
        sb_amp = d_current * I_r * 0.08   # up to 8% of rated at critical
        sb_lo  = sinusoid(F_SIDEBAND_LO, sb_amp)
        sb_hi  = sinusoid(F_SIDEBAND_HI, sb_amp)
        current = [current[i] + sb_lo[i] + sb_hi[i] for i in range(n)]

        # Phase asymmetry → current mean creeps up (one phase draws more)
        asymm  = I_r * d_current * 0.07
        current = [current[i] + asymm for i in range(n)]

        # Torque pulsations at 2×slip frequency (2 Hz) → current oscillation
        torque_mod = sinusoid(F_2SLIP, d_current * I_r * 0.04)
        current = [current[i] + torque_mod[i] for i in range(n)]

        # Occasional sharp transients as cracks propagate under thermal cycling
        current = add_impulses(current, d_current * 3.0,
                               d_current * I_r * 0.15, decay=0.40)

        # Increased noise (harmonic distortion worsens)
        current = [current[i] + random.gauss(0, d_current * 4.0)
                   for i in range(n)]

    save_max_min_csvs('current', data_dir, ts, current)
    logger.info(f'  Current dev={d_current:.3f}  '
                f'peak={max(current):.1f}A  mean={sum(current)/n:.1f}A')

    # -- AUDIO ----------------------------------------------------------------
    # Healthy: 50 Hz dominant hum + harmonics
    audio = [MOTOR['audio_db'] + random.gauss(0, 1.2) for _ in range(n)]
    h50   = sinusoid(50, 4.0)
    h100  = sinusoid(100, 1.8)
    audio = [audio[i] + h50[i] + h100[i] for i in range(n)]

    if d_audio > 0.01:
        # 100 Hz (2× supply) becomes dominant - magnetic force waves at 2× frequency
        # In healthy motor this is small; broken bars create strong 2× component
        h100_extra = sinusoid(100, d_audio * 12.0)
        h200       = sinusoid(200, d_audio * 5.0)
        audio = [audio[i] + h100_extra[i] + h200[i] for i in range(n)]

        # Sidebands in audio at supply ± 2×slip (electromagnetically induced)
        audio_sb_lo = sinusoid(F_SIDEBAND_LO, d_audio * 4.0)
        audio_sb_hi = sinusoid(F_SIDEBAND_HI, d_audio * 4.0)
        audio = [audio[i] + audio_sb_lo[i] + audio_sb_hi[i] for i in range(n)]

        # Overall dB rise from increased magnetic noise
        audio = [audio[i] + d_audio * 8.0 + random.gauss(0, 1.5)
                 for i in range(n)]

    save_max_min_csvs('audio', data_dir, ts, audio)
    logger.info(f'  Audio  dev={d_audio:.3f}  '
                f'mean={sum(audio)/n:.2f}dB  peak={max(audio):.2f}dB')

    # -- ACCELERATION ---------------------------------------------------------
    # Healthy: low broadband + 1× rotational
    accel = [MOTOR['accel_rms_g'] + random.gauss(0, 0.06) for _ in range(n)]
    rot1x = sinusoid(F_ROT, 0.15)
    accel = [accel[i] + rot1x[i] for i in range(n)]

    if d_accel > 0.01:
        # Torque ripple at 2×slip creates mechanical vibration at 2 Hz
        torque_vib = sinusoid(F_2SLIP, d_accel * 0.8)
        accel = [accel[i] + torque_vib[i] for i in range(n)]

        # 1× rotational grows (asymmetric magnetic pull → unbalanced force)
        rot_extra = sinusoid(F_ROT, d_accel * 0.6)
        accel = [accel[i] + rot_extra[i] for i in range(n)]

        # Periodic torque impulses (each rotor revolution, bar fault fires)
        accel = add_impulses(accel, F_ROT * d_accel,
                             d_accel * 1.2, decay=0.65)

        # Broadband vibration rises
        accel = [accel[i] + random.gauss(0, d_accel * 0.25)
                 for i in range(n)]

    save_max_min_csvs('acceleration', data_dir, ts, accel)
    logger.info(f'  Accel  dev={d_accel:.3f}  '
                f'peak={max(accel):.3f}g  rms={math.sqrt(sum(v**2 for v in accel)/n):.3f}g')

    # Motor electrical fault failure threshold: current dev >= 0.80 (insulation breakdown)
    return d_current >= 0.80


if __name__ == '__main__':
    run_fault_simulation(FAULT_NAME, generate,
                          sleep_seconds=30,
                          data_dir=LOCAL_DATA_DIR)
